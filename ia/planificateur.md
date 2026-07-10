# Planificateur de recherche

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-10 (v2.1.0).
> Masters non modifiés ; données de sources publiques ; **la notice PDF fait foi.**

**Objectif.** Transforme une question en plan de recherche (sans y répondre) : concept, synonymes, catégories, contrats candidats, notices, critères de complétude.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.


## Comment l'utiliser (sans LLM)
1. Repérer dans la question un ou plusieurs **concepts** via leurs **synonymes** (voir [concepts](concepts.md) / [planificateur.json](planificateur.json)).
2. Récupérer le **plan** du concept : contrats candidats + catégories à consulter + notices.
3. Consulter les pages catégorie et fiches contrat listées ; collecter les éléments **avec leur source**.
4. Vérifier la **complétude** ([couverture-recherche](couverture-recherche.md)).
5. Assembler une réponse **sourcée** ([méthode](methode-question-complexe.md)). En cas d'absence : le dire, ne pas inventer.

## Plans par concept

### Invalidité
- Synonymes : invalidit, ipt, ipp, ptia, incapacit
- Catégories à consulter : garanties, exclusions, definitions, conditions, declencheurs, plafonds, franchises, options, cotisations, delais, fiscalite, points-vigilance, formules
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT

### Décès
- Synonymes : deces, décès, mortalit, capital deces
- Catégories à consulter : garanties, exclusions, definitions, conditions, declencheurs, plafonds, options, cotisations, delais, fiscalite, points-vigilance, formules
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Essen'Ciel Patrimoine, Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT

### Décès accidentel
- Synonymes : accidentel
- Catégories à consulter : exclusions, declencheurs, franchises, options, delais, points-vigilance
- Contrats candidats : Entour'Age, Essen'Ciel (assurance obsèques), Ma Protection Accident (Garantie des accidents de la vie)

### Accident
- Synonymes : accident
- Catégories à consulter : garanties, exclusions, definitions, declencheurs, plafonds, franchises, options, delais, points-vigilance
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Masterlife CREDIT

### Hospitalisation
- Synonymes : hospitalis
- Catégories à consulter : garanties, exclusions, definitions, options, delais, points-vigilance
- Contrats candidats : Avizen Pro, Entour'Age, Masterlife CREDIT

### Incapacité temporaire
- Synonymes : incapacite temporaire, itt, indemnite journaliere, indemnités journalières
- Catégories à consulter : garanties, exclusions, definitions, conditions, declencheurs, plafonds, franchises, options, delais, points-vigilance, formules
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Excelium (assurance vie), Masterlife CREDIT

### Carence / délai d'attente
- Synonymes : carence, delai d attente, delai de carence, attente
- Catégories à consulter : exclusions, definitions, conditions, declencheurs, franchises, options, points-vigilance
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques)

### Rachat
- Synonymes : rachat, valeur de rachat, mise en reduction, reduction
- Catégories à consulter : garanties, exclusions, definitions, plafonds, options, cotisations, delais, fiscalite, points-vigilance, formules
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Essen'Ciel Patrimoine, Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT

### Souscription & adhésion
- Synonymes : souscription, adhesion, adherer, formalite, questionnaire
- Catégories à consulter : garanties, exclusions, definitions, conditions, declencheurs, plafonds, franchises, options, cotisations, delais, fiscalite, points-vigilance, formules
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Essen'Ciel Patrimoine, Excelium (assurance vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT

### Âge
- Synonymes : age a l adhesion, age maximal, age minimal, ans inclus, annee de naissance
- Catégories à consulter : conditions, cotisations
- Contrats candidats : Avizen, Entour'Age

### Suicide
- Synonymes : suicide
- Catégories à consulter : exclusions
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Essen'Ciel Patrimoine, Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Masterlife CREDIT

### Bénéficiaire
- Synonymes : beneficiaire, clause beneficiaire
- Catégories à consulter : garanties, exclusions, definitions, plafonds, options, delais, fiscalite, points-vigilance
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Essen'Ciel Patrimoine, Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT

### Fiscalité
- Synonymes : fiscal, 990, 757, impot, succession, abattement, cgi
- Catégories à consulter : garanties, definitions, conditions, declencheurs, options, cotisations, delais, fiscalite, points-vigilance
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Essen'Ciel Patrimoine, Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT

### Fin de garantie
- Synonymes : fin de garantie, cesse, terme, expiration, resiliation
- Catégories à consulter : garanties, exclusions, declencheurs, plafonds, options, cotisations, delais, fiscalite
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Essen'Ciel (assurance obsèques), Essen'Ciel Patrimoine, Excelium (assurance vie), Ma Protection Accident (Garantie des accidents de la vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT

### Association / ANPERE
- Synonymes : anpere, association, gestion paritaire
- Catégories à consulter : garanties, conditions, cotisations
- Contrats candidats : Avizen, Avizen Pro, Entour'Age, Excelium (assurance vie), Ma Retraite (plan d'épargne retraite individuel — PER), Masterlife CREDIT
