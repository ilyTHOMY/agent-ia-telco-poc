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
    verifier_pin, obtenir_solde, obtenir_historique_transactions,
    declencher_remboursement, bloquer_compte, mettre_a_jour_nom_client,
)
from backend.mocks.crm_api import creer_ticket
from backend.mocks.notifications import notifier_escalade
from backend.mocks.agents_network import (
    lister_agents_par_quartier, lister_agents_disponibles
)

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
WOLOF_CONTEXT_PATH = Path(__file__).parent.parent / "prompts" / "wolof_context.txt"

INTENTIONS_TICKET_DIRECT = {
    "pin_oublie": ("P3", "Client a oublie son PIN"),
}


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
        model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
        generation_config={
            "temperature": 0.1,
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

    async def traiter_message(self, id_session, telephone, message, canal="chat"):
        ctx = await self.gestionnaire.obtenir(id_session)
        if not ctx:
            ctx = await self.gestionnaire.creer(id_session, telephone, canal)

        ctx.ajouter_message("human", message)

        if not ctx.authentifie:
            reponse = await self._gerer_auth(ctx, message)
            await self.gestionnaire.sauvegarder(ctx)
            return reponse

        analyse = analyser_message(message)
        ctx.intention_courante = analyse["intention"]["id"]
        ctx.entites_courantes  = analyse["entites"]
        ctx.sentiment_courant  = analyse["sentiment"]
        ctx.langue             = analyse["langue"]["langue"]
        self._maj_compteur(ctx, analyse)

        action = await self._action_directe(ctx, analyse, message)
        if action:
            ctx.incomprehensions_consecutives = 0
            await self.gestionnaire.sauvegarder(ctx)
            return action

        ticket_direct = await self._ticket_direct(ctx, analyse)
        if ticket_direct:
            await self.gestionnaire.sauvegarder(ctx)
            return ticket_direct

        escalade = self.escalade_engine.evaluer(message, analyse, ctx, ctx.transaction_courante)
        if escalade:
            return await self._escalader(ctx, escalade)

        operateur = ctx.client.get("operateur") if ctx.client else None
        contexte_rag = recuperer_contexte(message, operateur=operateur, top_k=3)
        reponse_ia = await self._appeler_gemini(ctx, message, analyse, contexte_rag)

        if getattr(ctx, 'incomprehensions_consecutives', 0) >= 2:
            esc = self.escalade_engine.evaluer(message, analyse, ctx, ctx.transaction_courante)
            if esc:
                return await self._escalader(ctx, esc)

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

    async def _gerer_auth(self, ctx, message):
        if not ctx.telephone or ctx.telephone == "":
            ctx.telephone = message.strip().replace(" ", "")
            reponse = "Entrez votre code PIN a 4 chiffres."
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}

        res = verifier_pin(ctx.telephone, message.strip())

        if not res["succes"]:
            ctx.tentatives_pin += 1
            reponse = res.get("erreur", "PIN incorrect.")
            if res.get("bloque"):
                reponse = "Compte bloque. Contactez votre operateur."
            ctx.ajouter_message("assistant", reponse)
            return {"reponse": reponse, "authentifie": False, "escalade": False}

        client = res["client"]
        ctx.client = client
        ctx.authentifie = True
        ctx.tentatives_pin = 0
        ctx.incomprehensions_consecutives = 0

        if client.get("langue"):
            ctx.langue = client["langue"]

        nom = client.get("nom", "Client")
        prenom = nom.split()[0] if nom else "Client"
        operateur = client.get("operateur", "").replace("_", " ").title()

        if ctx.langue == "wo":
            reponse = f"Salaam aleekum {prenom} ! Connecte naa la ci {operateur}. Naka laa mana defe ?"
        else:
            reponse = f"Bonjour {prenom} ! Connecte sur {operateur}. Comment puis-je vous aider ?"

        ctx.ajouter_message("assistant", reponse)
        return {
            "reponse": reponse,
            "authentifie": True,
            "nouveau_client": res.get("nouveau_client", False),
            "client": {
                "nom": client.get("nom"),
                "operateur": operateur,
                "statut_compte": client.get("statut_compte"),
                "plafond_journalier_xof": client.get("plafond_journalier_xof"),
                "nouveau_client": res.get("nouveau_client", False),
            },
            "escalade": False,
        }

    async def _action_directe(self, ctx, analyse, message_original) -> Optional[dict]:
        intention = analyse["intention"]["id"]
        telephone = ctx.telephone
        msg_lower = message_original.lower()

        # ── Solde ─────────────────────────────────────────────────────────────
        if intention == "consulter_solde":
            res = obtenir_solde(telephone)
            if res["succes"]:
                solde  = res["solde_xof"]
                plafond = res["plafond_journalier_xof"]
                if ctx.langue == "wo":
                    texte = f"Sama kalpae bi : {solde:,} XOF.\nLimite : {plafond:,} XOF/jour."
                else:
                    texte = f"Solde : **{solde:,} XOF** · Plafond/jour : {plafond:,} XOF"
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        # ── Historique ────────────────────────────────────────────────────────
        elif intention == "historique_transactions":
            res = obtenir_historique_transactions(telephone, limite=3)
            if res["succes"] and res["transactions"]:
                lignes = [
                    f"• {t['type'].title()} {t['montant_xof']:,} XOF — "
                    f"{t['statut'].replace('_',' ')} ({t['reference']})"
                    for t in res["transactions"]
                ]
                texte = "3 dernieres operations :\n" + "\n".join(lignes)
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        # ── Agent proche — avec demande de quartier ───────────────────────────
        elif intention == "demander_agent_proche":
            operateur = ctx.client.get("operateur") if ctx.client else None

            # Extraire quartier du message
            quartier = _extraire_quartier(message_original, ctx)

            if not quartier:
                # Pas de quartier mentionne → demander
                texte = (
                    "Pour vous trouver l'agent le plus proche, "
                    "dans quel quartier ou ville vous trouvez-vous ?"
                )
                # Stocker qu'on attend un quartier
                ctx.entites_courantes["attente_quartier"] = True
                ctx.ajouter_message("assistant", texte)
                ctx.tentatives_resolution = 0
                return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

            # Chercher par quartier
            res = lister_agents_par_quartier(quartier, operateur=operateur)
            ctx.entites_courantes.pop("attente_quartier", None)

            if res["agents"]:
                agent = res["agents"][0]
                loc   = agent.get("localisation", {})
                texte = (
                    f"Agent disponible a {loc.get('quartier',quartier)} :\n"
                    f"**{agent['nom']}** — {loc.get('adresse','')}\n"
                    f"Tel : {agent.get('telephone','—')} · "
                    f"Note : {agent.get('note',0)}/5 · "
                    f"Flotte : {agent.get('solde_flotte_xof',0):,} XOF"
                )
            else:
                quartiers = res.get("quartiers_disponibles", [])
                texte = (
                    f"Je n'ai pas d'agent disponible a {quartier}. "
                    f"Zones avec agents disponibles : {', '.join(quartiers[:5]) if quartiers else 'aucune'}."
                )

            ctx.ajouter_message("assistant", texte)
            ctx.tentatives_resolution = 0
            return {"reponse": texte, "intention": intention, "escalade": False, "tickets": []}

        # ── Attente quartier (message suivant apres "dans quel quartier ?") ──
        elif ctx.entites_courantes.get("attente_quartier"):
            operateur = ctx.client.get("operateur") if ctx.client else None
            quartier  = message_original.strip()
            res = lister_agents_par_quartier(quartier, operateur=operateur)
            ctx.entites_courantes.pop("attente_quartier", None)

            if res["agents"]:
                agent = res["agents"][0]
                loc   = agent.get("localisation", {})
                texte = (
                    f"Agent disponible a {loc.get('quartier', quartier)} :\n"
                    f"**{agent['nom']}** — {loc.get('adresse','')}\n"
                    f"Tel : {agent.get('telephone','—')} · "
                    f"Note : {agent.get('note',0)}/5 · "
                    f"Flotte : {agent.get('solde_flotte_xof',0):,} XOF"
                )
            else:
                quartiers = res.get("quartiers_disponibles", [])
                texte = (
                    f"Pas d'agent disponible a {quartier}. "
                    f"Zones disponibles : {', '.join(quartiers[:5]) if quartiers else 'aucune'}."
                )

            ctx.ajouter_message("assistant", texte)
            return {"reponse": texte, "intention": "demander_agent_proche", "escalade": False, "tickets": []}

        return None

    async def _ticket_direct(self, ctx, analyse) -> Optional[dict]:
        intention = analyse["intention"]["id"]
        if intention not in INTENTIONS_TICKET_DIRECT:
            return None

        priorite, description = INTENTIONS_TICKET_DIRECT[intention]
        res = creer_ticket(
            telephone=ctx.telephone,
            type_reclamation=intention,
            description=f"{description} — via {ctx.canal}",
            historique=ctx.formater_historique_prompt(),
            priorite=priorite,
            canal=ctx.canal,
            id_client=ctx.client.get("id") if ctx.client else None,
        )

        if not res["succes"]:
            return None

        ticket = res["ticket"]
        id_ticket = ticket["id"]
        ctx.tickets_crees.append(id_ticket)

        if intention == "pin_oublie":
            texte = (
                "Pour reinitialiser votre PIN : ouvrez l'application > "
                "'PIN oublie' > entrez votre numero > recevez un OTP > definissez un nouveau PIN. "
                f"Si le probleme persiste, ticket cree : **{id_ticket}**."
            )
        else:
            texte = f"Demande enregistree. Reference : **{id_ticket}** — traitement sous {ticket['sla_heures']}h."

        ctx.ajouter_message("assistant", texte)
        return {
            "reponse": texte,
            "intention": intention,
            "escalade": False,
            "id_ticket": id_ticket,
            "tickets": ctx.tickets_crees,
        }

    async def _appeler_gemini(self, ctx, message, analyse, contexte_rag) -> str:
        print(f"[GEMINI DEBUG] contexte_rag={contexte_rag[:200] if contexte_rag else 'VIDE'}")
        langue    = analyse["langue"]["langue"]
        sentiment = analyse["sentiment"]
        instruction_langue = adapter_langue_reponse(langue)
        instruction_ton    = adapter_ton_reponse(sentiment)

        wolof_extra = ""
        if langue in ("wo", "fr-wo") and self.wolof_context:
            wolof_extra = f"\n{self.wolof_context}"

        prompt = f"""{self.system_prompt}

LANGUE: {instruction_langue}{wolof_extra}
TON: {instruction_ton}
CLIENT: {ctx.formater_contexte_client()}
HISTORIQUE: {ctx.formater_historique_prompt()}
BASE CONNAISSANCE: {contexte_rag or "Aucune info specifique."}
MESSAGE: {message}
REPONSE (2-3 phrases max, directe):"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[GEMINI] Erreur : {e}")
            return "Je rencontre une difficulte technique. Reessayez dans un instant."

    def _maj_compteur(self, ctx, analyse):
        if not hasattr(ctx, 'incomprehensions_consecutives'):
            ctx.incomprehensions_consecutives = 0
        if not hasattr(ctx, 'derniere_intention'):
            ctx.derniere_intention = None
        intention = analyse["intention"]["id"]
        if intention == "inconnu":
            ctx.incomprehensions_consecutives += 1
        elif intention == ctx.derniere_intention and ctx.tentatives_resolution > 0:
            ctx.incomprehensions_consecutives += 1
        else:
            ctx.incomprehensions_consecutives = 0
        ctx.derniere_intention = intention

    async def _escalader(self, ctx, escalade) -> dict:
        regle    = escalade["regle"]
        client   = ctx.client or {}
        nom      = (client.get("nom") or "Client").split()[0]
        res_ticket = creer_ticket(
            telephone=ctx.telephone,
            type_reclamation=regle["id"],
            description=f"Escalade : {regle['nom']}. {escalade['message_declencheur'][:200]}",
            historique=ctx.formater_historique_prompt(),
            priorite=regle["priorite"],
            canal=ctx.canal,
            id_transaction=ctx.transaction_courante.get("id") if ctx.transaction_courante else None,
            id_client=client.get("id"),
        )
        id_ticket = res_ticket["ticket"]["id"] if res_ticket["succes"] else "INC-ERR"
        ctx.tickets_crees.append(id_ticket)
        ctx.escalade_effectuee = True
        ctx.incomprehensions_consecutives = 0

        sla = regle["sla_minutes"]
        delai = f"{sla} min" if sla < 60 else f"{sla//60}h"
        notifier_escalade(ctx.telephone, id_ticket, delai, canal="sms")

        msg = self.escalade_engine.generer_message_escalade(escalade, langue=ctx.langue, nom_client=nom)
        msg_complet = f"{msg}\n\nReference : **{id_ticket}** — {regle['priorite']} — sous {delai}"

        ctx.ajouter_message("assistant", msg_complet)
        await self.gestionnaire.sauvegarder(ctx)

        return {
            "reponse": msg_complet,
            "escalade": True,
            "regle_escalade": regle["id"],
            "priorite": regle["priorite"],
            "id_ticket": id_ticket,
            "intention": ctx.intention_courante,
            "tickets": ctx.tickets_crees,
        }


def _extraire_quartier(message: str, ctx) -> Optional[str]:
    """
    Extrait le quartier depuis le message.
    Cherche les noms de quartiers connus de Dakar/Thies.
    """
    QUARTIERS = [
        "medina", "plateau", "grand dakar", "parcelles", "guediawaye",
        "pikine", "thies", "saint-louis", "ziguinchor", "kaolack",
        "hlm", "liberté", "mermoz", "sacre coeur", "almadies",
        "yoff", "ngor", "ouakam", "fann", "gueule tapee",
        "biscuiterie", "colobane", "tilene", "rebeuss",
    ]
    msg = message.lower()
    for q in QUARTIERS:
        if q in msg:
            return q.title()

    # Chercher "a X" ou "au X" ou "dans X"
    import re
    match = re.search(r'\b(?:a|au|dans|vers|à)\s+([a-zA-ZÀ-ÿ\s-]{3,20})', msg)
    if match:
        return match.group(1).strip().title()

    return None


_orchestrateur = None

def get_orchestrateur():
    if _orchestrateur is None:
        raise RuntimeError("Orchestrateur non initialise.")
    return _orchestrateur

def init_orchestrateur(gestionnaire):
    global _orchestrateur
    _orchestrateur = Orchestrateur(gestionnaire)
    return _orchestrateur
