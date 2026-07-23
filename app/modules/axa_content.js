// axa_content — contenu éditorial de l'espace AXA Conseiller (Lot 1) :
// tutoriel « Premiers pas » + page « Utiliser AXA avec ChatGPT / Claude » + prompts copiables.
// Contenu MÉTHODOLOGIQUE et prudent : aucune donnée contractuelle inventée ; la preuve reste
// toujours le contrat / la notice PDF / la source officielle. Rendu via Markdown sécurisé.

export const TUTORIEL = `
## Qu'est-ce qu'AXA Conseiller ?

AXA Conseiller est un **espace de travail** qui rassemble la connaissance contractuelle AXA
(garanties, exclusions, options, cotisations, fiscalité, points de vigilance, notices PDF) et des
outils pour t'aider à **chercher, comparer, préparer un rendez-vous et répondre prudemment**.

> ⚠️ **Règle d'or.** L'outil t'aide à raisonner et à retrouver l'information. **La réponse finale
> donnée au client s'appuie toujours sur le contrat, la notice PDF ou une source officielle.**
> Aucun conseil personnalisé définitif n'est produit automatiquement.

## Pack A et Pack B : ne jamais les confondre

- **Pack A (stable)** = la **référence de vérité contractuelle**. C'est lui qui fait foi : contrats,
  garanties, exclusions, conditions, sources officielles, garde-fous.
- **Pack B (matrices, expérimental)** = une **couche de raisonnement** pour comparer des mécaniques
  entre contrats sur les cas complexes.

**Quand utiliser Pack A ?** Presque toujours : question sur un contrat, une garantie, une exclusion,
une condition, une preuve, une règle officielle simple.

**Quand utiliser Pack B ?** Uniquement pour *réfléchir* : besoin client multi-contrats, confusion
fréquente entre deux mécaniques, préparation d'un rendez-vous complexe.

> 🚫 **Pack B n'est JAMAIS une preuve client.** Une matrice éclaire un raisonnement ; elle ne
> remplace jamais le contrat. Ne cite jamais une matrice comme justification à un client.

## Les gestes du quotidien

1. **Chercher une info contrat** → *Recherche contrat* : filtre par famille, ouvre la fiche,
   déplie Garanties / Exclusions / Cotisations / Fiscalité / Vigilance.
2. **Chercher une garantie ou une exclusion précise** → *Recherche globale* : tape le mot
   (« décès », « franchise », « rachat »…). Les résultats sont sourcés et surlignés.
3. **Vérifier une exclusion** → ouvre la fiche du contrat, section *Exclusions importantes*,
   puis **ouvre la notice PDF** pour confirmer avant toute réponse au client.
4. **Préparer un rendez-vous** → *Préparation RDV* : génère une fiche (objectifs, questions,
   points de vigilance, contrats à vérifier, sources à ouvrir, formulations prudentes).
5. **Analyser un besoin** → *Analyse des besoins* : renseigne la situation, l'outil propose des
   **pistes** de familles/contrats à explorer — **il ne décide pas à ta place**.
6. **Comparer deux contrats** → *avec ton IA* : donne-lui l'adresse de la Vue IA (voir
   « Utiliser avec une IA ») — elle dispose du comparateur et des matrices. La fiche contrat
   garde le bloc « à ne pas confondre » (contrats proches d'une même famille).
7. **Accéder aux sources** → *Sources officielles* (manifeste des masters) et *PDF contractuels*
   (notices et conditions générales, qui font foi).
8. **Mode IA / audit** → bascule 👤/🤖 en haut de l'app : la vue IA affiche les données brutes
   complètes (traçabilité, JSON) pour vérifier une source ou préparer un pack pour un assistant.

## Éviter les erreurs courantes

- ❌ Répondre au client à partir d'une matrice (Pack B) → ✅ toujours revenir au contrat / PDF.
- ❌ Donner un chiffre fiscal ou social « au doigt mouillé » → ✅ pas de calcul définitif sans
  source officielle **et** données client complètes.
- ❌ Conclure quand la source est absente → ✅ dire ce qui manque et où vérifier.
- ❌ Confondre deux contrats d'une même famille → ✅ vérifier la section « à ne pas confondre ».

## Limites à respecter

- L'outil **ne stocke aucune donnée client** dans le projet (recueil local uniquement).
- Les aides « questions à poser / cas d'usage / erreurs » sont **méthodologiques et génériques** :
  elles ne remplacent pas la lecture du contrat pour le cas précis.
- Aucune IA n'est branchée : l'« Assistant IA » prépare des prompts et des packs à utiliser dans
  ChatGPT ou Claude, sans envoi automatique.
`;

// Prompts prêts à copier. Chaque prompt embarque les garde-fous (Pack A = preuve, Pack B ≠ preuve,
// réponse = contrat/PDF/source, citer les sources, refuser si source insuffisante).
const GARDE_FOUS = `Règles impératives :
- Pack A = référence contractuelle qui fait foi. Pack B = raisonnement uniquement, jamais une preuve.
- Toute affirmation contractuelle doit citer sa source (contrat, notice PDF, page si disponible).
- Si la source est absente ou insuffisante, dis-le clairement et n'invente rien.
- Aucun conseil personnalisé définitif, aucun calcul fiscal/social définitif sans source officielle et données complètes.
- Termine par les limites de ta réponse et où le conseiller doit vérifier.`;


// Repères MÉTHODOLOGIQUES par famille de contrats (Lot 3). Ce ne sont PAS des affirmations
// contractuelles : ce sont des aides génériques au raisonnement. La vérité reste le contrat/PDF.
export const FAMILLE_META = {
  "prévoyance": {
    cible: "Personnes souhaitant protéger leurs proches et/ou leurs revenus en cas de décès, accident ou invalidité.",
    questions: ["Situation familiale et personnes à charge ?", "Revenus à protéger et capital souhaité ?",
      "État de santé (questionnaire médical) ?", "Contrats de prévoyance déjà détenus ?", "Budget de cotisation ?"],
    cas_usage: ["Protéger sa famille en cas de décès", "Maintenir un revenu en cas d'invalidité/incapacité", "Prévoir les frais d'obsèques"],
    erreurs: ["Confondre garantie décès et garantie invalidité", "Oublier les délais de carence et exclusions", "Négliger le questionnaire médical"],
  },
  "épargne": {
    cible: "Épargnant cherchant à valoriser un capital, financer un projet ou organiser une transmission.",
    questions: ["Objectif et horizon de placement ?", "Capital initial et versements prévus ?", "Tolérance au risque ?",
      "Bénéficiaires envisagés ?", "Fiscalité recherchée ?"],
    cas_usage: ["Constituer une épargne de moyen/long terme", "Préparer une transmission", "Se constituer un complément"],
    erreurs: ["Promettre un rendement", "Négliger la clause bénéficiaire", "Ignorer les frais et le choix des supports"],
  },
  "retraite": {
    cible: "Actif préparant un complément de revenu pour la retraite.",
    questions: ["Âge et horizon retraite ?", "Tranche marginale d'imposition ?", "Capacité d'épargne régulière ?",
      "Statut (salarié / indépendant) ?", "Sortie envisagée en capital ou en rente ?"],
    cas_usage: ["Se constituer un complément de retraite", "Optimiser la déduction fiscale des versements"],
    erreurs: ["Affirmer un gain fiscal sans connaître la TMI", "Oublier le blocage de l'épargne jusqu'à la retraite", "Négliger les cas de déblocage anticipé"],
  },
  "assurance_emprunteur": {
    cible: "Emprunteur devant assurer un crédit (souvent immobilier).",
    questions: ["Montant, durée et type de prêt ?", "Quotité d'assurance par emprunteur ?", "État de santé et profession ?",
      "Pratiques à risque / tabagisme ?", "Assurance déléguée ou groupe ?"],
    cas_usage: ["Couvrir un prêt immobilier (décès, invalidité, incapacité)"],
    erreurs: ["Mal fixer la quotité", "Négliger les exclusions liées au métier/loisirs", "Ignorer le droit de substitution d'assurance"],
  },
};
// Objectifs client → famille de contrats (aide au tri, jamais une reco définitive).
export const OBJECTIFS = [
  { label: "Protéger ma famille / mes revenus", famille: "prévoyance" },
  { label: "Prévoir mes obsèques", famille: "prévoyance" },
  { label: "Épargner / valoriser un capital", famille: "épargne" },
  { label: "Organiser une transmission", famille: "épargne" },
  { label: "Préparer ma retraite", famille: "retraite" },
  { label: "Assurer un crédit / prêt", famille: "assurance_emprunteur" },
];
export const ERREURS_TRANSVERSES = [
  "Citer une matrice (Pack B) comme preuve à un client",
  "Donner un chiffre fiscal ou social définitif sans source officielle et données complètes",
  "Conclure alors que la source est absente ou insuffisante",
];

