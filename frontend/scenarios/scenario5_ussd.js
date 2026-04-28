/**
 * Scenario 5 — USSD & Wolof, client rural
 * Telephone : +221784567890
 * Canal : USSD #150#
 */
const SCENARIO_5 = {
  id: "S5",
  titre: "USSD & Wolof — Client rural",
  telephone: "+221784567890",
  canal: "ussd",
  code_ussd: "*150#",
  navigation: [
    { saisie: "",    note: "Ouverture session USSD" },
    { saisie: "2",   note: "Signaler une transaction" },
    { saisie: "2*2", note: "Retrait echoue" },
  ],
  description: "Client sans smartphone, zone rurale. Navigation USSD uniquement via chiffres. L'arbre de navigation guide vers la resolution du retrait echoue avec confirmation SMS.",
};

// Pour le simulateur USSD frontend
async function lancerScenario5() {
  // Cette fonction est utilisee par ussd.html
  // Elle pre-remplit et execute la navigation automatiquement
  const steps = [
    { action: "start", code: "*150#", tel: "+221784567890" },
    { action: "nav", saisie: "2", delai: 1500 },
    { action: "nav", saisie: "2", delai: 1500 },
  ];
  return steps;
}

if (typeof module !== "undefined") module.exports = { SCENARIO_5, lancerScenario5 };
