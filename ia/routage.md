# Routage par type de question

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-16 (v2.2.0).
> Masters non modifiés ; données de sources publiques ; **la notice PDF fait foi.**
> IA : n'utilise jamais ta mémoire générale ici — cite [Contrat — Notice, p.X] ou signale l'absence. Première visite : [START](https://gabuz22.github.io/AXA/ia/start.html).

**Objectif.** Comment le système détermine le périmètre, les contrats retenus, les catégories et le déclenchement des sources officielles. Le contrat explicitement nommé verrouille la recherche.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.

## Détection d'entités (dérivée, sans LLM)
- **Contrat explicite** : nom/variantes détectés dans la question → **verrouillage** du périmètre.
- **Concept principal / secondaires** : concepts dont un synonyme apparaît, classés par pertinence (score 0-5).
- **Type de question** : mono-contrat · transversale · comparaison · réglementaire · ambiguë.
- **Catégories demandées** : barème→formules/garanties/définitions · définition→définitions · franchise→franchises · exclusion→exclusions · etc.
- **Dimension réglementaire** : détectée sur des **mots de la question** (déductible, fiscal, succession, âge légal, Sécurité sociale…), pas sur le concept.

## Règles de routage
1. **Contrat explicite nommé** → **mono-contrat verrouillé** (les autres contrats sont *rejetés*), sauf demande de comparaison / d'alternatives / « autres contrats ».
2. **Comparaison** (`compare A et B`) → **uniquement** A et B.
3. **Transversale** (`quels contrats…`) → contrats classés par **score de pertinence** ; 4-5 d'abord, 1-3 signalés à part.
4. **Réglementaire** → contrat d'abord si utile, **puis** sources officielles adaptées.
5. **Strictement contractuelle** (garantie, exclusion, barème, franchise, plafond, déclencheur d'un contrat) → **aucune source officielle externe** par défaut.

## Déclenchement des sources officielles
Requis **uniquement** si la question porte sur : fiscalité, déductibilité, plafond légal, âge légal, retraite/PER (fiscal), succession, protection/Sécurité sociale, droit de l'assurance, obligation réglementaire, définition légale.
**Jamais** pour une garantie/exclusion/définition/barème/délai/franchise/déclencheur/plafond **contractuels**.

Format machine : [routage.json](routage.json) (analyse des 10 questions de validation).

## Validation — 10 questions

- **Quel est le barème d'invalidité d'Avizen Pro ?**
  - entités : contrat=['avizen-pro'] · concept=invalidite · secondaires=—
  - périmètre : **mono-contrat** (mono-contrat)
  - contrats retenus : avizen-pro
  - contrats rejetés : 8
  - catégories : formules, garanties, definitions
  - source officielle : **False**
  - statut : **conclusion_documentee**

- **Quelle est la définition d'un accident dans Ma Protection Accident ?**
  - entités : contrat=['ma-protection-accident-garantie-des-accidents-de-la-vie'] · concept=accident · secondaires=—
  - périmètre : **mono-contrat** (mono-contrat)
  - contrats retenus : ma-protection-accident-garantie-des-accidents-de-la-vie
  - contrats rejetés : 8
  - catégories : definitions
  - source officielle : **False**
  - statut : **conclusion_documentee**

- **Quels contrats parlent d'invalidité ?**
  - entités : contrat=aucun · concept=invalidite · secondaires=—
  - périmètre : **multi-contrats** (transversale)
  - contrats retenus : avizen, avizen-pro, masterlife-credit, essen-ciel-assurance-obseques, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, entour-age, excelium-assurance-vie
  - contrats rejetés : 1
  - catégories : —
  - source officielle : **False**
  - statut : **conclusion_documentee**

- **Compare Avizen Pro et Masterlife Crédit sur l'invalidité.**
  - entités : contrat=['avizen-pro', 'masterlife-credit'] · concept=invalidite · secondaires=—
  - périmètre : **comparaison** (comparaison)
  - contrats retenus : avizen-pro, masterlife-credit
  - contrats rejetés : 7
  - catégories : —
  - source officielle : **False**
  - statut : **conclusion_documentee**

- **Quels contrats excluent le suicide ?**
  - entités : contrat=aucun · concept=suicide · secondaires=—
  - périmètre : **multi-contrats** (transversale)
  - contrats retenus : avizen, avizen-pro, entour-age, essen-ciel-assurance-obseques, essen-ciel-patrimoine, excelium-assurance-vie, ma-protection-accident-garantie-des-accidents-de-la-vie, masterlife-credit
  - contrats rejetés : 1
  - catégories : exclusions
  - source officielle : **False**
  - statut : **conclusion_documentee**

- **Jusqu'à quel âge les versements sur PER sont-ils déductibles ?**
  - entités : contrat=['ma-retraite-plan-d-epargne-retraite-individuel-per'] · concept=— · secondaires=—
  - périmètre : **mono-contrat** (reglementaire)
  - contrats retenus : ma-retraite-plan-d-epargne-retraite-individuel-per
  - contrats rejetés : 8
  - catégories : —
  - source officielle : **True**
  - statut : **verification_source_officielle_requise**

- **Quelle est la franchise contractuelle d'Avizen Pro ?**
  - entités : contrat=['avizen-pro'] · concept=— · secondaires=—
  - périmètre : **mono-contrat** (mono-contrat)
  - contrats retenus : avizen-pro
  - contrats rejetés : 8
  - catégories : franchises
  - source officielle : **False**
  - statut : **donnees_insuffisantes**

- **Quels autres contrats traitent de l'invalidité en plus d'Avizen Pro ?**
  - entités : contrat=['avizen-pro'] · concept=invalidite · secondaires=—
  - périmètre : **mono+transversal** (mono-contrat)
  - contrats retenus : avizen-pro, avizen, masterlife-credit, essen-ciel-assurance-obseques, ma-protection-accident-garantie-des-accidents-de-la-vie, ma-retraite-plan-d-epargne-retraite-individuel-per, entour-age, excelium-assurance-vie
  - contrats rejetés : 1
  - catégories : —
  - source officielle : **False**
  - statut : **conclusion_documentee**

- **Cette garantie dépend-elle de la Sécurité sociale ?**
  - entités : contrat=aucun · concept=— · secondaires=—
  - périmètre : **ambigu** (reglementaire)
  - contrats retenus : —
  - contrats rejetés : 9
  - catégories : garanties
  - source officielle : **True**
  - statut : **verification_source_officielle_requise**

- **Je ne trouve pas de plafond chiffré : puis-je conclure qu'il n'y en a pas ?**
  - entités : contrat=aucun · concept=— · secondaires=—
  - périmètre : **ambigu** (ambigu)
  - contrats retenus : —
  - contrats rejetés : 9
  - catégories : plafonds
  - source officielle : **False**
  - statut : **verification_notice_requise**
