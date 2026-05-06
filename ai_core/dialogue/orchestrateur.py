"""
Orchestrateur v3 — corrections :
- Gemini plus rapide : prompt reduit, temperature basse, max_tokens reduit
- Compteur incomprehensions_consecutives pour escalade reelle
- Reset du compteur quand client repond positivement
- Litige agent bien detecte avant demande humain
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
    verifier_pin, obtenir_solde, obtenir_client_par_telephone,
    obtenir_historique_transactions, declencher_remboursement, bloquer_compte,
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
        model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash-preview-04-17"),
        generation_config={
            # Temperature basse = reponses plus directes et plus rapides
            "temperature": 0.1,
            # Reduit le nombre de tokens = reponse plus rapide
            "max_output_tokens": int(os.getenv("LLM_MAX_TOKENS", "512")),
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

        # Auth
        if not ctx.authentifie:
            reponse = await self._gerer_auth(ctx, message)
            await self.gestionnaire.sauvegarder(ctx)
            return reponse

        # NLU
        analyse = analyser_message(message)
        ctx.intention_courante = analyse["intention"]["id"]
        ctx.entites_courantes  = analyse["entites"]
        ctx.sentiment_courant  = analyse["sentiment"]
        ctx.langue             = analyse["langue"]["langue"]

        # Mettre a jour le compteur incomprehensions
        self._maj_compteur_incomprehensions(ctx, analyse)

        # Actions directes sans Gemini
        action = await self._action_directe(ctx, analyse)
        if action:
            ctx.incomprehensions_consecutives = 0
            await self.gestionnaire.sauvegarder(ctx)
            return action

        # Escalade pre-reponse
        escalade = self.escalade_engine.evaluer(
            message, analyse, ctx, ctx.transaction_courante)
        if escalade:
            return await self._escalader(ctx, escalade)

        # RAG — contexte limite pour aller plus vite
        operateur = ctx.client.get("operateur") if ctx.client else None
        contexte_rag = recuperer_contexte(message, operateur=operateur, top_k=2)

        # Gemini
        reponse_ia = await self._appeler_gemini(ctx, message, analyse, contexte_rag)

        # Escalade post-reponse : seulement si 2 incomprehensions consecutives
        if getattr(ctx, 'incomprehensions_consecutives', 0) >= 2:
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

    def _maj_compteur_incomprehensions(self, ctx, analyse: dict):
        """
        Incremente le compteur seulement si :
        - L'intention est 'inconnu' (IA ne comprend pas)
        - Ou c'est la meme intention que le message precedent sans resolution
        Reset si l'intention est claire et differente.
        """
        if not hasattr(ctx, 'incomprehensions_consecutives'):
            ctx.incomprehensions_consecutives = 0
        if not hasattr(ctx, 'derniere_intention'):
            ctx.derniere_intention = None

        intention = analyse["intention"]["id"]

        if intention == "inconnu":
            ctx.incomprehensions_consecutives += 1
        elif intention == ctx.derniere_intention and ctx.tentatives_resolution > 0:
            # Meme intention posee deux fois = client ne comprend pas la reponse
            ctx.incomprehensions_consecutives += 1
        else:
            # Nouvelle intention claire = reset
            ctx.incomprehensions_consecutives = 0

        ctx.derniere_intention = intention

    async def _gerer_auth(self, ctx, message: str) -> dict:
 
        # ── Etape 1 : Numero de telephone ─────────────────────────────────────────
        if not ctx.telephone or ctx.telephone == "":
            telephone = message.strip().replace(" ", "")
            ctx.telephone = telephone
            reponse = "Entrez votre code PIN a 4 chiffres pour vous connecter."
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}
    
        # ── Etape 3 : Collecte du nom (nouveau client en attente de nom) ──────────
        if getattr(ctx, 'attente_nom', False):
            nom_saisi = message.strip()
    
            if len(nom_saisi) < 2:
                reponse = "Veuillez entrer votre nom complet (ex: Moussa Diallo)."
                ctx.ajouter_message("assistant", reponse)
                return {"reponse": reponse, "authentifie": False, "escalade": False}
    
            # Enregistrer le nom dans clients.json
            from backend.mocks.mobile_money_api import mettre_a_jour_nom_client
            mettre_a_jour_nom_client(ctx.telephone, nom_saisi)
    
            # Mettre a jour le profil en session
            if ctx.client:
                ctx.client["nom"] = nom_saisi
    
            ctx.attente_nom = False
            ctx.authentifie = True
    
            prenom = nom_saisi.split()[0]
            operateur = ctx.client.get("operateur", "").replace("_", " ").title() if ctx.client else ""
            plafond = ctx.client.get("plafond_journalier_xof", 100000) if ctx.client else 100000
    
            if ctx.langue == "wo":
                reponse = (
                    f"Salaam aleekum {prenom} ! Compte bi bugul ci {operateur}. "
                    f"Limite journaliere : {plafond:,} XOF. "
                    f"Naka laa mana defe ?"
                )
            else:
                reponse = (
                    f"Bienvenue {prenom} ! Votre compte {operateur} a ete cree avec succes. "
                    f"Plafond actuel : {plafond:,} XOF/jour. "
                    f"Completez votre verification d'identite (KYC) pour augmenter vos limites. "
                    f"Comment puis-je vous aider ?"
                )
    
            ctx.ajouter_message("assistant", reponse)
            return {
                "reponse": reponse,
                "authentifie": True,
                "nouveau_client": True,
                "client": {
                    "nom": nom_saisi,
                    "operateur": operateur,
                    "statut_compte": ctx.client.get("statut_compte") if ctx.client else "actif",
                    "plafond_journalier_xof": plafond,
                    "nouveau_client": True,
                },
                "escalade": False,
            }
    
        # ── Etape 2 : PIN ──────────────────────────────────────────────────────────
        from backend.mocks.mobile_money_api import verifier_pin
        pin = message.strip()
        telephone = ctx.telephone
        res = verifier_pin(telephone, pin)
    
        if not res["succes"]:
            ctx.tentatives_pin += 1
            reponse = res.get("erreur", "PIN incorrect.")
            if res.get("bloque"):
                reponse = (
                    "Votre compte a ete bloque apres plusieurs tentatives. "
                    "Contactez votre operateur pour le debloquer."
                )
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}
    
        # Auth reussie
        client = res["client"]
        ctx.client = client
        ctx.tentatives_pin = 0
        ctx.incomprehensions_consecutives = 0
    
        if client.get("langue"):
            ctx.langue = client["langue"]
    
        nouveau = res.get("nouveau_client", False)
    
        # ── Nouveau client : demander le nom avant de continuer ───────────────────
        if nouveau:
            ctx.attente_nom = True
            # Ne pas marquer authentifie=True encore
            reponse = (
                "Bienvenue ! Je vois que c'est votre premiere connexion. "
                "Quel est votre nom complet ?"
            )
            ctx.ajouter_message("assistant", reponse)
            return {
                "reponse": reponse,
                "authentifie": False,
                "nouveau_client": True,
                "escalade": False,
            }
    
        # ── Client existant : connexion directe ───────────────────────────────────
        ctx.authentifie = True
        nom = client.get("nom", "").split()[0] if client.get("nom") else "Client"
        operateur = client.get("operateur", "").replace("_", " ").title()
    
        if ctx.langue == "wo":
            reponse = f"Salaam aleekum {nom} ! Connecte naa la ci {operateur}. Naka laa mana defe ?"
        else:
            reponse = f"Bonjour {nom} ! Connecte sur {operateur}. Comment puis-je vous aider ?"
    
        ctx.ajouter_message("assistant", reponse)
        return {
            "reponse": reponse,
            "authentifie": True,
            "nouveau_client": False,
            "client": {
                "nom": client.get("nom"),
                "operateur": operateur,
                "statut_compte": client.get("statut_compte"),
                "plafond_journalier_xof": client.get("plafond_journalier_xof"),
                "nouveau_client": False,
            },
            "escalade": False,
        }

    async def _action_directe(self, ctx, analyse: dict) -> Optional[dict]:
        intention = analyse["intention"]["id"]
        telephone = ctx.telephone

        if intention == "consulter_solde":
            res = obtenir_solde(telephone)
            if res["succes"]:
                solde = res["solde_xof"]
                plafond = res["plafond_journalier_xof"]
                if ctx.langue == "wo":
                    texte = f"Sama kalpae bi : {solde:,} XOF.\nLimite : {plafond:,} XOF/jour."
                else:
                    texte = f"Solde : **{solde:,} XOF** · Plafond/jour : {plafond:,} XOF"
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        elif intention == "historique_transactions":
            res = obtenir_historique_transactions(telephone, limite=3)
            if res["succes"] and res["transactions"]:
                lignes = [
                    f"• {t['type'].title()} {t['montant_xof']:,} XOF — "
                    f"{t['statut'].replace('_',' ')} ({t['reference']})"
                    for t in res["transactions"]
                ]
                texte = "3 dernières opérations :\n" + "\n".join(lignes)
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
                    f"Agent disponible : **{agent['nom']}** — "
                    f"{loc.get('quartier','')}, {loc.get('ville','')}\n"
                    f"Flotte : {agent.get('solde_flotte_xof',0):,} XOF · Note : {agent.get('note',0)}/5"
                )
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        return None

    async def _appeler_gemini(self, ctx, message: str, analyse: dict, contexte_rag: str) -> str:
        langue = analyse["langue"]["langue"]
        sentiment = analyse["sentiment"]

        instruction_langue = adapter_langue_reponse(langue)
        instruction_ton = adapter_ton_reponse(sentiment)

        wolof_extra = ""
        if langue in ("wo", "fr-wo") and self.wolof_context:
            wolof_extra = f"\n{self.wolof_context}"

        # Prompt compact pour reponse rapide
        prompt = f"""{self.system_prompt}

LANGUE: {instruction_langue}{wolof_extra}
TON: {instruction_ton}

CLIENT: {ctx.formater_contexte_client()}

HISTORIQUE (3 derniers echanges):
{ctx.formater_historique_prompt()}

BASE CONNAISSANCE:
{contexte_rag or "Pas d'info specifique. Repondre avec prudence."}

MESSAGE: {message}

REPONSE (courte, 2-3 phrases max, directe):"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[GEMINI] Erreur : {e}")
            return (
                "Desolee, je rencontre une difficulte technique. "
                "Reessayez dans un instant ou contactez directement votre operateur."
            )

    async def _escalader(self, ctx, escalade: dict) -> dict:
        regle = escalade["regle"]
        client = ctx.client or {}
        nom = (client.get("nom") or "Client").split()[0]
        telephone = ctx.telephone

        res_ticket = creer_ticket(
            telephone=telephone,
            type_reclamation=regle["id"],
            description=(
                f"Escalade : {regle['nom']}. "
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
        ctx.incomprehensions_consecutives = 0

        sla = regle["sla_minutes"]
        delai = f"{sla} min" if sla < 60 else f"{sla//60}h"
        notifier_escalade(telephone, id_ticket, delai, canal="sms")

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


_orchestrateur: Optional[Orchestrateur] = None

def get_orchestrateur() -> Orchestrateur:
    if _orchestrateur is None:
        raise RuntimeError("Orchestrateur non initialise.")
    return _orchestrateur

def init_orchestrateur(gestionnaire: GestionnaireContexte) -> Orchestrateur:
    global _orchestrateur
    _orchestrateur = Orchestrateur(gestionnaire)
    return _orchestrateur