# Graphe documentaire

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-17 (v2.3.0).
> Outil **indépendant et non officiel**, non affilié ni validé par AXA — documents accessibles publiquement.
> Masters non modifiés ; **la notice PDF fait foi** ; vérification humaine avant toute réponse au client.
> IA : n'utilise jamais ta mémoire générale ici — cite [Contrat — Notice, p.X] ou signale l'absence. Première visite : [START](https://gabuz22.github.io/AXA/ia/start.html).

**Objectif.** Nœuds (contrats, concepts, éléments, notices, autorités) et relations dérivées. Aucune inférence.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.

## Contenu
- **692 nœuds**, **2195 relations**. Types de nœuds : contrat, concept, garantie, exclusion, définition, condition, déclencheur, notice, article réglementaire.
- Relations dérivées : `appartient_a` (élément→contrat), `concerne` (élément→concept), `source` (élément→notice), `reglementation_recommandee` (concept→autorité).
- Aucune relation inventée ; tout est vérifiable dans les pages.

Format machine : [graphe.json](graphe.json).
