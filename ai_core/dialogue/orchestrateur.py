"""
Orchestrateur v2 — adapte aux nouvelles structures de donnees.
Changements :
- Auth : numero seul au premier message, PIN au second
- Nouveau client : creation automatique du profil
- intents.json unifie (plus de intents_fr/intents_wo)
- Tickets persistes dans tickets.json via crm_api v2
- CSAT declenche cote frontend apres resolution
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

# mocks v2/v3
from backend.mocks.mobile_money_api import (
    verifier_pin,
    obtenir_solde,
    obtenir_client_par_telephone,
    obtenir_historique_transactions,
    declencher_remboursement,
    bloquer_compte,
)
from backend.mocks.crm_api import creer_ticket, mettre_a_jour_ticket
from backend.mocks.notifications import notifier_escalade
from backend.mocks.agents_network import lister_agents_disponibles

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
WOLOF_CONTEXT_PATH = Path(__file__).parent.parent / "prompts" / "wolof_context.txt"


def _charger_prompt(chemin: Path, defaut: str = "") -> str:
    try:
        return chemin.read_text(encoding="utf-8")
    except FileNotFoundError:
        return defaut


def _configurer_gemini() -> genai.GenerativeModel:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY manquant dans .env")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
        generation_config={
            "temperature": 0.35,
            "max_output_tokens": int(os.getenv("LLM_MAX_TOKENS", "1024")),
        },
    )


class Orchestrateur:

    def __init__(self, gestionnaire: GestionnaireContexte):
        self.gestionnaire = gestionnaire
        self.escalade_engine = MoteurEscalade()
        self.model = _configurer_gemini()
        self.system_prompt = _charger_prompt(SYSTEM_PROMPT_PATH,
            "Tu es un agent IA de support client Mobile Money UEMOA.")
        self.wolof_context = _charger_prompt(WOLOF_CONTEXT_PATH, "")

    # ── Point d'entree principal ───────────────────────────────────────────────

    async def traiter_message(
        self,
        id_session: str,
        telephone: str,
        message: str,
        canal: str = "chat",
    ) -> dict:
        ctx = await self.gestionnaire.obtenir(id_session)
        if not ctx:
            ctx = await self.gestionnaire.creer(id_session, telephone, canal)

        ctx.ajouter_message("human", message)

        # ── Etape 1 : Authentification ─────────────────────────────────────────
        if not ctx.authentifie:
            reponse = await self._gerer_auth(ctx, message)
            await self.gestionnaire.sauvegarder(ctx)
            return reponse

        # ── Etape 2 : Analyse NLU ─────────────────────────────────────────────
        analyse = analyser_message(message)
        ctx.intention_courante = analyse["intention"]["id"]
        ctx.entites_courantes  = analyse["entites"]
        ctx.sentiment_courant  = analyse["sentiment"]
        ctx.langue             = analyse["langue"]["langue"]

        # ── Etape 3 : Actions directes (solde, historique, agent) ─────────────
        action = await self._action_directe(ctx, analyse)
        if action:
            await self.gestionnaire.sauvegarder(ctx)
            return action

        # ── Etape 4 : Evaluation escalade pre-reponse ─────────────────────────
        escalade = self.escalade_engine.evaluer(
            message, analyse, ctx, ctx.transaction_courante)
        if escalade:
            return await self._escalader(ctx, escalade)

        # ── Etape 5 : RAG ─────────────────────────────────────────────────────
        operateur = ctx.client.get("operateur") if ctx.client else None
        contexte_rag = recuperer_contexte(message, operateur=operateur, top_k=3)

        # ── Etape 6 : Gemini ──────────────────────────────────────────────────
        reponse_ia = await self._appeler_gemini(ctx, message, analyse, contexte_rag)

        # ── Etape 7 : Evaluation post-reponse ────────────────────────────────
        ctx.incrementer_tentatives()
        if ctx.tentatives_resolution >= 2:
            esc_post = self.escalade_engine.evaluer(message, analyse, ctx, ctx.transaction_courante)
            if esc_post:
                return await self._escalader(ctx, esc_post)

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

    async def _gerer_auth(self, ctx: ContexteConversation, message: str) -> dict:
        """
        Flux auth v2 :
        - Si pas de telephone en session → le message EST le telephone
        - Si telephone present → le message EST le PIN
        """
        # Etape A : reception du numero de telephone
        if not ctx.telephone or ctx.telephone == "":
            # Le message est le numero
            telephone = message.strip().replace(" ", "")
            ctx.telephone = telephone
            reponse = (
                f"Bienvenue ! Entrez votre code PIN a 4 chiffres pour vous connecter."
            )
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}

        # Etape B : reception du PIN
        pin = message.strip()
        telephone = ctx.telephone

        res = verifier_pin(telephone, pin)

        if not res["succes"]:
            ctx.tentatives_pin += 1
            reponse = res.get("erreur", "PIN incorrect.")
            if res.get("bloque"):
                reponse = (
                    "Votre compte a ete bloque apres plusieurs tentatives incorrectes. "
                    "Contactez votre operateur pour debloquer votre compte."
                )
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}

        # Auth reussie
        client = res["client"]
        ctx.client = client
        ctx.authentifie = True
        ctx.tentatives_pin = 0

        # Detecter langue depuis profil client si disponible
        if client.get("langue"):
            ctx.langue = client["langue"]

        nom = client.get("nom", "").split()[0] if client.get("nom") else "Client"
        operateur = client.get("operateur", "").replace("_", " ").title()
        nouveau = res.get("nouveau_client", False)

        if ctx.langue == "wo":
            reponse = (
                f"Salaam aleekum {nom} ! Connecte naa la ci {operateur}. "
                f"Naka laa mana defe ?"
            )
        else:
            if nouveau:
                reponse = (
                    f"Bienvenue {nom} ! Votre compte a ete cree avec succes. "
                    f"Pour l'instant votre plafond journalier est de "
                    f"{client.get('plafond_journalier_xof', 100000):,} XOF. "
                    f"Pour augmenter vos limites, completez votre verification d'identite (KYC). "
                    f"Comment puis-je vous aider ?"
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
            "nouveau_client": nouveau,
            "client": {
                "nom": client.get("nom"),
                "operateur": operateur,
                "statut_compte": client.get("statut_compte"),
                "plafond_journalier_xof": client.get("plafond_journalier_xof"),
                "nouveau_client": nouveau,
            },
            "escalade": False,
        }

    # ── Actions directes ───────────────────────────────────────────────────────

    async def _action_directe(
        self, ctx: ContexteConversation, analyse: dict
    ) -> Optional[dict]:
        intention = analyse["intention"]["id"]
        telephone = ctx.telephone

        if intention == "consulter_solde":
            res = obtenir_solde(telephone)
            if res["succes"]:
                solde = res["solde_xof"]
                plafond = res["plafond_journalier_xof"]
                if ctx.langue == "wo":
                    texte = f"Sama kalpae bi : {solde:,} XOF.\nLimite journaliere : {plafond:,} XOF."
                else:
                    texte = (
                        f"Votre solde actuel est de **{solde:,} XOF**.\n"
                        f"Plafond journalier : {plafond:,} XOF."
                    )
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        elif intention == "historique_transactions":
            res = obtenir_historique_transactions(telephone, limite=3)
            if res["succes"] and res["transactions"]:
                txns = res["transactions"]
                lignes = [
                    f"• {t['type'].title()} {t['montant_xof']:,} XOF — "
                    f"{t['statut'].replace('_',' ')} ({t['reference']})"
                    for t in txns
                ]
                texte = "Vos 3 dernières opérations :\n" + "\n".join(lignes)
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        elif intention == "demander_agent_proche":
            operateur = ctx.client.get("operateur") if ctx.client else None
            res = lister_agents_disponibles(operateur=operateur)
            if res["succes"] and res["agents"]:
                agent = res["agents"][0]
                loc = agent.get("localisation", {})
                texte = (
                    f"L'agent disponible le mieux noté est :\n"
                    f"**{agent['nom']}** — {loc.get('quartier','')}, {loc.get('ville','')}\n"
                    f"Solde : {agent.get('solde_flotte_xof',0):,} XOF · Note : {agent.get('note',0)}/5"
                )
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        return None

    # ── Gemini ─────────────────────────────────────────────────────────────────

    async def _appeler_gemini(
        self,
        ctx: ContexteConversation,
        message: str,
        analyse: dict,
        contexte_rag: str,
    ) -> str:
        langue = analyse["langue"]["langue"]
        sentiment = analyse["sentiment"]

        instruction_langue = adapter_langue_reponse(langue)
        instruction_ton = adapter_ton_reponse(sentiment)

        # Contexte wolof supplementaire
        wolof_extra = ""
        if langue in ("wo", "fr-wo") and self.wolof_context:
            wolof_extra = f"\n\n{self.wolof_context}"

        prompt = f"""{self.system_prompt}

## LANGUE
{instruction_langue}{wolof_extra}

## TON
{instruction_ton}

## CONTEXTE CLIENT
{ctx.formater_contexte_client()}

## HISTORIQUE (derniers echanges)
{ctx.formater_historique_prompt()}

## BASE DE CONNAISSANCES VERIFIEE
{contexte_rag or "Aucun document pertinent trouve. Repondre avec prudence."}

## MESSAGE CLIENT
{message}

## REPONSE :"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[GEMINI] Erreur : {e}")
            return (
                "Je rencontre une difficulte technique momentanee. "
                "Veuillez reessayer ou contacter directement votre operateur."
            )

    # ── Escalade ───────────────────────────────────────────────────────────────

    async def _escalader(self, ctx: ContexteConversation, escalade: dict) -> dict:
        regle = escalade["regle"]
        client = ctx.client or {}
        nom = (client.get("nom") or "Client").split()[0]
        telephone = ctx.telephone

        # Creer ticket dans tickets.json
        res_ticket = creer_ticket(
            telephone=telephone,
            type_reclamation=regle["id"],
            description=(
                f"Escalade automatique : {regle['nom']}. "
                f"Message : {escalade['message_declencheur'][:200]}"
            ),
            priorite=regle["priorite"],
            canal=ctx.canal,
            id_transaction=(
                ctx.transaction_courante.get("id")
                if ctx.transaction_courante else None
            ),
            id_client=client.get("id"),
        )

        id_ticket = res_ticket["ticket"]["id"] if res_ticket["succes"] else "INC-ERR"
        ctx.tickets_crees.append(id_ticket)
        ctx.escalade_effectuee = True

        # Notification SMS
        sla = regle["sla_minutes"]
        delai = f"{sla} min" if sla < 60 else f"{sla//60}h"
        notifier_escalade(telephone, id_ticket, delai, canal="sms")

        # Message selon langue
        msg_esc = self.escalade_engine.generer_message_escalade(
            escalade, langue=ctx.langue, nom_client=nom
        )
        msg_complet = (
            f"{msg_esc}\n\n"
            f"Reference : **{id_ticket}** — {regle['priorite']} — traitement sous {delai}"
        )

        ctx.ajouter_message("assistant", msg_complet)
        await self.gestionnaire.sauvegarder(ctx)

        return {
            "reponse": msg_complet,
            "escalade": True,
            "regle_escalade": regle["id"],
            "priorite": regle["priorite"],
            "id_ticket": id_ticket,
            "cible": regle["cible"],
            "intention": ctx.intention_courante,
            "tickets": ctx.tickets_crees,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_orchestrateur: Optional[Orchestrateur] = None

def get_orchestrateur() -> Orchestrateur:
    if _orchestrateur is None:
        raise RuntimeError("Orchestrateur non initialise.")
    return _orchestrateur

def init_orchestrateur(gestionnaire: GestionnaireContexte) -> Orchestrateur:
    global _orchestrateur
    _orchestrateur = Orchestrateur(gestionnaire)
    return _orchestrateur
