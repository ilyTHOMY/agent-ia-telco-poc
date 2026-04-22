"""
Orchestrateur principal — coeur de l'agent IA.
Coordonne : NLU → Auth → Mock API → RAG → Gemini → Escalade → Reponse.
Point d'entree unique pour traiter un message client.
"""
import os
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from ai_core.nlu.intent_classifier import analyser_message
from ai_core.nlu.language_detect import adapter_langue_reponse
from ai_core.nlu.sentiment import adapter_ton_reponse
from ai_core.rag.retriever import recuperer_contexte
from ai_core.dialogue.context_manager import ContexteConversation, GestionnaireContexte
from ai_core.dialogue.escalade_engine import MoteurEscalade
from backend.mocks.mobile_money_api import (
    obtenir_client_par_telephone,
    obtenir_solde,
    verifier_statut_compte,
    obtenir_historique_transactions,
    declencher_remboursement,
    bloquer_compte,
)
from backend.mocks.crm_api import creer_ticket, mettre_a_jour_ticket
from backend.mocks.notifications import notifier_escalade, notifier_resolution
from backend.mocks.agents_network import lister_agents_proches

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"


def _charger_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "Tu es un agent IA de support client Mobile Money UEMOA."


def _configurer_gemini() -> genai.GenerativeModel:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY manquant dans .env")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
        generation_config={
            "temperature": 0.3,
            "max_output_tokens": int(os.getenv("LLM_MAX_TOKENS", "1024")),
        },
    )


class Orchestrateur:
    """
    Orchestre le traitement complet d'un message client.
    Une instance par application (singleton).
    """

    def __init__(self, gestionnaire_contexte: GestionnaireContexte):
        self.gestionnaire = gestionnaire_contexte
        self.escalade_engine = MoteurEscalade()
        self.model = _configurer_gemini()
        self.system_prompt = _charger_system_prompt()

    # ── Point d'entree principal ───────────────────────────────────────────────

    async def traiter_message(
        self,
        id_session: str,
        telephone: str,
        message: str,
        canal: str = "chat",
    ) -> dict:
        """
        Traite un message client et retourne la reponse complete.
        Cree la session si elle n'existe pas.
        """
        # 1. Recuperer ou creer le contexte
        ctx = await self.gestionnaire.obtenir(id_session)
        if not ctx:
            ctx = await self.gestionnaire.creer(id_session, telephone, canal)

        ctx.ajouter_message("human", message)

        # 2. Authentification
        if not ctx.authentifie:
            reponse = await self._gerer_authentification(ctx, message)
            await self.gestionnaire.sauvegarder(ctx)
            return reponse

        # 3. Analyse NLU
        analyse = analyser_message(message)
        ctx.intention_courante = analyse["intention"]["id"]
        ctx.entites_courantes = analyse["entites"]
        ctx.sentiment_courant = analyse["sentiment"]
        ctx.langue = analyse["langue"]["langue"]

        # 4. Actions autonomes selon l'intention
        reponse_action = await self._executer_action(ctx, analyse)
        if reponse_action:
            await self.gestionnaire.sauvegarder(ctx)
            return reponse_action

        # 5. Evaluer escalade pre-reponse
        transaction = ctx.transaction_courante
        escalade = self.escalade_engine.evaluer(message, analyse, ctx, transaction)
        if escalade:
            return await self._gerer_escalade(ctx, escalade)

        # 6. RAG — recuperer contexte FAQ
        operateur = ctx.client.get("operateur") if ctx.client else None
        contexte_rag = recuperer_contexte(message, operateur=operateur, top_k=3)

        # 7. Construire prompt et appeler Gemini
        reponse_ia = await self._appeler_gemini(ctx, message, analyse, contexte_rag)

        # 8. Evaluer escalade post-reponse
        ctx.incrementer_tentatives()
        if ctx.tentatives_resolution >= 2:
            escalade_post = self.escalade_engine.evaluer(message, analyse, ctx, transaction)
            if escalade_post:
                return await self._gerer_escalade(ctx, escalade_post)

        ctx.ajouter_message("assistant", reponse_ia)
        await self.gestionnaire.sauvegarder(ctx)

        return {
            "reponse": reponse_ia,
            "intention": ctx.intention_courante,
            "sentiment": ctx.sentiment_courant,
            "langue": ctx.langue,
            "escalade": False,
            "tickets": ctx.tickets_crees,
        }

    # ── Authentification ───────────────────────────────────────────────────────

    async def _gerer_authentification(self, ctx: ContexteConversation, message: str) -> dict:
        """
        Gere le flux d'authentification PIN.
        Etape 1 : verification du PIN via mock API.
        """
        client = obtenir_client_par_telephone(ctx.telephone)

        if not client:
            reponse = (
                "Bonjour ! Je ne trouve pas de compte associe a ce numero. "
                "Etes-vous bien inscrit chez Wave, Orange Money ou Mixx by Yas ? "
                "Si vous souhaitez vous inscrire, rendez-vous dans une agence ou sur l'application."
            )
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}

        # Verifier le PIN
        pin_saisi = message.strip()
        pin_correct = client.get("pin", "")

        if pin_saisi != pin_correct:
            ctx.tentatives_pin += 1
            if ctx.tentatives_pin >= 3:
                bloquer_compte(ctx.telephone, "3 tentatives PIN incorrectes")
                reponse = (
                    "Votre compte a ete temporairement bloque apres 3 tentatives incorrectes. "
                    "Contactez votre operateur au 3330 (Wave), 888 (Orange Money) ou 3232 (Mixx) "
                    "pour debloquer votre compte."
                )
            else:
                restantes = 3 - ctx.tentatives_pin
                reponse = (
                    f"PIN incorrect. Il vous reste {restantes} tentative(s). "
                    "Veuillez reessayer."
                )
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}

        # Auth reussie
        ctx.client = client
        ctx.authentifie = True
        ctx.langue = client.get("langue", "fr")
        ctx.tentatives_pin = 0

        nom = client.get("nom", "").split()[0]  # Prenom uniquement
        operateur = client.get("operateur", "").replace("_", " ").title()

        if ctx.langue == "wo":
            reponse = (
                f"Salaam aleekum {nom} ! Connecte naa la ci {operateur}. "
                f"Naka laa mana defe ? (Lii moo ngi mel ni : solde, transaction, reclamation...)"
            )
        else:
            reponse = (
                f"Bonjour {nom} ! Vous etes connecte a votre compte {operateur}. "
                f"Comment puis-je vous aider aujourd'hui ?"
            )

        ctx.ajouter_message("assistant", reponse)
        return {
            "reponse": reponse,
            "authentifie": True,
            "client": {
                "nom": client.get("nom"),
                "operateur": operateur,
                "segment": client.get("segment"),
            },
            "escalade": False,
        }

    # ── Actions autonomes ──────────────────────────────────────────────────────

    async def _executer_action(self, ctx: ContexteConversation, analyse: dict) -> Optional[dict]:
        """
        Execute les actions directes ne necessitant pas Gemini.
        Retourne None si Gemini doit prendre le relai.
        """
        intention = analyse["intention"]["id"]
        telephone = ctx.telephone

        # Consultation solde
        if intention == "consulter_solde":
            res = obtenir_solde(telephone)
            if res["succes"]:
                solde = res["solde_xof"]
                plafond = res["plafond_journalier_xof"]
                if ctx.langue == "wo":
                    reponse = (
                        f"Sama kalpae bi : {solde:,} XOF. "
                        f"Limite journaliere yi : {plafond:,} XOF."
                    )
                else:
                    reponse = (
                        f"Votre solde actuel est de {solde:,} XOF. "
                        f"Votre plafond journalier est de {plafond:,} XOF."
                    )
                ctx.ajouter_message("assistant", reponse)
                ctx.tentatives_resolution = 0
                return {"reponse": reponse, "intention": intention, "escalade": False, "tickets": []}

        # Historique transactions
        if intention == "historique_transactions":
            res = obtenir_historique_transactions(telephone, limite=3)
            if res["succes"] and res["transactions"]:
                txns = res["transactions"]
                lignes = []
                for t in txns:
                    statut = t["statut"].replace("_", " ")
                    lignes.append(
                        f"- {t['type'].title()} : {t['montant_xof']:,} XOF — {statut} ({t['reference']})"
                    )
                reponse = "Vos 3 dernieres operations :\n" + "\n".join(lignes)
                ctx.ajouter_message("assistant", reponse)
                ctx.tentatives_resolution = 0
                return {"reponse": reponse, "intention": intention, "escalade": False, "tickets": []}

        # Agent le plus proche
        if intention == "demander_agent_proche":
            # Dakar centre par defaut (a remplacer par GPS client en prod)
            res = lister_agents_proches(14.6937, -17.4441,
                                        operateur=ctx.client.get("operateur") if ctx.client else None)
            if res["succes"] and res["agents"]:
                agent = res["agents"][0]
                loc = agent["localisation"]
                reponse = (
                    f"L'agent le plus proche disponible est : {agent['nom']} "
                    f"({loc['quartier']}, {loc['ville']}) a {agent['distance_km']} km. "
                    f"Solde disponible : {agent['solde_flotte_xof']:,} XOF. "
                    f"Note client : {agent['note']}/5."
                )
                ctx.ajouter_message("assistant", reponse)
                ctx.tentatives_resolution = 0
                return {"reponse": reponse, "intention": intention, "escalade": False, "tickets": []}

        return None  # Gemini prend le relai

    # ── Appel Gemini ───────────────────────────────────────────────────────────

    async def _appeler_gemini(
        self,
        ctx: ContexteConversation,
        message: str,
        analyse: dict,
        contexte_rag: str,
    ) -> str:
        """
        Construit le prompt complet et appelle Gemini 2.5 Flash.
        """
        langue = analyse["langue"]["langue"]
        sentiment = analyse["sentiment"]

        instruction_langue = adapter_langue_reponse(langue)
        instruction_ton = adapter_ton_reponse(sentiment)

        prompt = f"""{self.system_prompt}

## INSTRUCTION LANGUE
{instruction_langue}

## INSTRUCTION TON
{instruction_ton}

## CONTEXTE CLIENT
{ctx.formater_contexte_client()}

## HISTORIQUE CONVERSATION (derniers echanges)
{ctx.formater_historique_prompt()}

## INFORMATIONS VERIFIEES (base de connaissances)
{contexte_rag if contexte_rag else "Aucune information specifique trouvee dans la base de connaissances."}

## MESSAGE DU CLIENT
{message}

## REPONSE DE L'AGENT IA :"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[GEMINI] Erreur : {e}")
            return (
                "Je rencontre une difficulte technique momentanee. "
                "Veuillez reessayer dans quelques instants ou contacter "
                "directement votre operateur."
            )

    # ── Gestion escalade ───────────────────────────────────────────────────────

    async def _gerer_escalade(self, ctx: ContexteConversation, escalade: dict) -> dict:
        """
        Gere l'escalade : cree le ticket, notifie client et conseiller.
        """
        regle = escalade["regle"]
        client = ctx.client or {}
        nom = client.get("nom", "Client").split()[0]
        telephone = ctx.telephone

        # Creer ticket CRM
        res_ticket = creer_ticket(
            telephone=telephone,
            type_reclamation=regle["id"],
            description=f"Escalade automatique : {regle['nom']}. Message : {escalade['message_declencheur'][:200]}",
            priorite=regle["priorite"],
            canal=ctx.canal,
            id_transaction=ctx.transaction_courante.get("id") if ctx.transaction_courante else None,
            id_client=client.get("id"),
        )

        id_ticket = res_ticket["ticket"]["id"] if res_ticket["succes"] else "INC-UNKNOWN"
        ctx.tickets_crees.append(id_ticket)
        ctx.escalade_effectuee = True

        # Notification client
        sla = regle["sla_minutes"]
        delai = f"{sla} min" if sla < 60 else f"{sla // 60}h"
        notifier_escalade(telephone, id_ticket, delai, canal="sms")

        # Message escalade adapte a la langue
        message_escalade = self.escalade_engine.generer_message_escalade(
            escalade, langue=ctx.langue, nom_client=nom
        )
        message_complet = (
            f"{message_escalade}\n\n"
            f"Reference de votre dossier : **{id_ticket}** "
            f"(priorite {regle['priorite']} — traitement sous {delai})"
        )

        ctx.ajouter_message("assistant", message_complet)
        await self.gestionnaire.sauvegarder(ctx)

        return {
            "reponse": message_complet,
            "escalade": True,
            "regle_escalade": regle["id"],
            "priorite": regle["priorite"],
            "id_ticket": id_ticket,
            "cible": regle["cible"],
            "intention": ctx.intention_courante,
            "tickets": ctx.tickets_crees,
        }


# ── Instance globale (initialisee dans main.py) ───────────────────────────────
_orchestrateur: Optional[Orchestrateur] = None


def get_orchestrateur() -> Orchestrateur:
    if _orchestrateur is None:
        raise RuntimeError("Orchestrateur non initialise. Appeler init_orchestrateur() d'abord.")
    return _orchestrateur


def init_orchestrateur(gestionnaire: GestionnaireContexte) -> Orchestrateur:
    global _orchestrateur
    _orchestrateur = Orchestrateur(gestionnaire)
    return _orchestrateur