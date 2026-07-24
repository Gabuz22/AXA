# Rapport de maturité — infrastructure de raisonnement

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-17 (v2.3.0).
> Outil **indépendant et non officiel**, non affilié ni validé par AXA — documents accessibles publiquement.
> Masters non modifiés ; **la notice PDF fait foi** ; vérification humaine avant toute réponse au client.
> IA : n'utilise jamais ta mémoire générale ici — cite [Contrat — Notice, p.X] ou signale l'absence. Première visite : [START](https://gabuz22.github.io/AXA/ia/start.html).

**Objectif.** Mesure des capacités de la Vue IA comme environnement documentaire pour un LLM.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.


| Capacité | Niveau | Détail |
|---|---|---|
| Capacité documentaire | élevée | Toutes les catégories exposées, sourcées, 100 % de couverture des données. |
| Capacité multi-contrats | élevée | Concepts, thèmes, comparateur, matrices croisées contrats × catégories. |
| Capacité réglementaire | moyenne (pointeurs, pas de contenu réglementaire) | Sources officielles par concept + détecteur de matière évolutive + surveillance (infra). |
| Capacité de preuve | élevée | Graphe de preuves + graphe documentaire ; chaque élément citable (id, source, page). |
| Capacité de couverture | élevée | Détecteur de couverture par concept + matrice de couverture + rapport global. |
| Capacité de navigation | élevée | Index, guide, outils, hiérarchie documentaire, choix des sources, liens stables. |
| Capacité de raisonnement | moyenne→élevée (cadre le LLM, ne le remplace pas) | Planificateur + méthode + choix des sources + conditions de non-conclusion. |

## Couverture des données (rappel)

- Résumé humain (resume_neutre) : 9/9
- Résumé IA (descriptions faits) : 91/91
- Garanties : 50/50
- Exclusions : 33/33
- Options : 36/36
- Cotisations & prix : 47/47
- Délais & franchises : 46/46
- Fiscalité : 44/44
- Points de vigilance : 61/61
- Formules : 22/22
- Définitions : 46/46
- Conditions : 21/21
- Déclencheurs : 83/83
- Plafonds : 53/53
- Franchises : 14/14
- Glossaire (définitions) : 46/46
- Notices (PDF) : 11/11
- Sources (références) : 164/164
- Contrats : 9/9

## Limites restantes
- Matching concept par mots-clés (large, non sémantique).
- Aucune donnée réglementaire stockée : uniquement des pointeurs à valider.
- Chiffres « à vérifier en notice » non extraits (signalés, jamais comblés).
- Régénération manuelle (`build_ia.py`).

## Rôle vis-à-vis d'un LLM
Le système **ne remplace pas** un LLM : il est le **meilleur environnement documentaire** pour lui — décomposition, parcours, preuves, couverture, arbitrage des sources, conditions de non-conclusion.