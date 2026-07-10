# Méthode — résoudre une question (simple ou complexe)

> Parcours standardisés pour une IA. Objectif : réponse **fiable, traçable, sourcée**, sans invention.

## Les 5 parcours

### 1. Question simple sur un contrat
« Quel est le plafond de cette garantie ? »
1. Ouvrir `/ia/contrat/<slug>.html`. 2. Repérer la garantie / le plafond. 3. Citer la notice + page.
**Complétude** : l'élément est présent et sourcé. Sinon → notice.

### 2. Question transversale
« Quels contrats traitent de l'invalidité ? »
1. `/ia/concepts.html#c-invalidite` (synonymes IPT/IPP/PTIA/incapacité). 2. Lister les **contrats concernés**.
3. Vérifier chaque contrat via `/ia/invalidite`… **Format** : liste des contrats + source par contrat.

### 3. Comparaison ciblée
« Compare les exclusions liées au suicide. »
1. `/ia/comparateur.html#s-suicide`. 2. Lire par contrat : exclusion + source + *absent de la base* le cas échéant.
**Ne pas** produire de conclusion commerciale. Toujours citer.

### 4. Question complexe avec conditions
« Dans quels cas l'invalidité déclenche-t-elle une prestation, avec quelles limites et exclusions ? »
1. **Planifier** : `/ia/planificateur.html` → concept invalidité → catégories (définitions, garanties, déclencheurs, exclusions, conditions) + contrats candidats.
2. **Collecter** les éléments par catégorie (avec sources).
3. **Vérifier la couverture** : `/ia/couverture-recherche.html#…` (qu'est-ce qui est absent ?).
4. **Assembler** (structure ci-dessous). 5. **Citer** chaque affirmation.

### 5. Information absente ou ambiguë
Si un élément est marqué *absent de la base* : dire **« non présent dans la base Gabriel AXA — à vérifier dans la notice / le certificat d'adhésion »**. **Ne jamais combler.** Distinguer : absent de la base ≠ absent du contrat ≠ renvoyé au certificat.

## Assembleur de réponse (structure obligatoire)
1. **Réponse courte** (sourcée).
2. **Conditions** (conditions de souscription / d'application).
3. **Exceptions / exclusions**.
4. **Limites** (plafonds, franchises, délais).
5. **Éléments non trouvés** (voir détecteur de couverture).
6. **Sources** (notice + page pour chaque affirmation, + `#id` des preuves).
7. **Niveau de certitude documentaire** : élevé (élément sourcé) · moyen (donnée à vérifier en notice) · faible (absent de la base).

## Règle d'or
Pack A = preuve · Pack B = raisonnement (jamais une preuve seule) · **la notice PDF fait foi** · ne jamais inventer.
