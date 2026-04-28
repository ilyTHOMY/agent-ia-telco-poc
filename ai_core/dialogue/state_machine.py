"""
Machine a etats de la conversation — gere les transitions entre etats.
Simplifie : l'orchestrateur reste le chef, la state machine est utilitaire.
"""
from enum import Enum


class EtatDialogue(str, Enum):
    ACCUEIL          = "accueil"
    AUTHENTIFICATION = "authentification"
    MENU_PRINCIPAL   = "menu_principal"
    DIAGNOSTIC       = "diagnostic"
    COLLECTE_INFO    = "collecte_info"
    ACTION           = "action"
    RESOLUTION       = "resolution"
    ESCALADE         = "escalade"
    CLOTURE          = "cloture"


TRANSITIONS = {
    EtatDialogue.ACCUEIL:          [EtatDialogue.AUTHENTIFICATION],
    EtatDialogue.AUTHENTIFICATION: [EtatDialogue.MENU_PRINCIPAL, EtatDialogue.ACCUEIL],
    EtatDialogue.MENU_PRINCIPAL:   [EtatDialogue.DIAGNOSTIC, EtatDialogue.ESCALADE, EtatDialogue.CLOTURE],
    EtatDialogue.DIAGNOSTIC:       [EtatDialogue.COLLECTE_INFO, EtatDialogue.ACTION, EtatDialogue.ESCALADE],
    EtatDialogue.COLLECTE_INFO:    [EtatDialogue.ACTION, EtatDialogue.ESCALADE],
    EtatDialogue.ACTION:           [EtatDialogue.RESOLUTION, EtatDialogue.ESCALADE, EtatDialogue.COLLECTE_INFO],
    EtatDialogue.RESOLUTION:       [EtatDialogue.CLOTURE, EtatDialogue.MENU_PRINCIPAL],
    EtatDialogue.ESCALADE:         [EtatDialogue.CLOTURE],
    EtatDialogue.CLOTURE:          [],
}


class StateMachine:
    def __init__(self):
        self.etat = EtatDialogue.ACCUEIL

    def peut_transitionner(self, nouvel_etat: EtatDialogue) -> bool:
        return nouvel_etat in TRANSITIONS.get(self.etat, [])

    def transitionner(self, nouvel_etat: EtatDialogue) -> bool:
        if self.peut_transitionner(nouvel_etat):
            self.etat = nouvel_etat
            return True
        return False

    def force_etat(self, etat: EtatDialogue) -> None:
        """Force un etat (usage interne orchestrateur)."""
        self.etat = etat

    def est_terminal(self) -> bool:
        return self.etat == EtatDialogue.CLOTURE

    def inferer_etat(self, intention: str, authentifie: bool, escalade: bool) -> EtatDialogue:
        """Infere l'etat suivant selon le contexte."""
        if not authentifie:
            return EtatDialogue.AUTHENTIFICATION
        if escalade:
            return EtatDialogue.ESCALADE
        if intention in ["salutation", "frais_et_limites"]:
            return EtatDialogue.MENU_PRINCIPAL
        if intention in ["transaction_non_recue", "retrait_echoue", "depot_non_credite",
                         "compte_bloque", "fraude_suspectee", "double_debit"]:
            return EtatDialogue.DIAGNOSTIC
        if intention in ["consulter_solde", "historique_transactions", "demander_agent_proche"]:
            return EtatDialogue.ACTION
        return EtatDialogue.MENU_PRINCIPAL
