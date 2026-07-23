# Outils IA — circulation & recherche

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-17 (v2.3.0).
> Outil **indépendant et non officiel**, non affilié ni validé par AXA — documents accessibles publiquement.
> Masters non modifiés ; **la notice PDF fait foi** ; vérification humaine avant toute réponse au client.
> IA : n'utilise jamais ta mémoire générale ici — cite [Contrat — Notice, p.X] ou signale l'absence. Première visite : [START](https://gabuz22.github.io/AXA/ia/start.html).

**Objectif.** Outils dérivés pour aider une IA à décomposer une question, parcourir les bons contrats, vérifier sa couverture et assembler une réponse sourcée.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.


- **[Niveaux de compétence](niveaux-competence.html)** — escalier de rigueur conseiller → inspecteur + grille d'auto-évaluation (JSON)
- **[Routage par type de question](routage.html)** — détection d'entités + verrouillage du contrat explicite + périmètre
- **[Pertinence pondérée](pertinence.html)** — score 0-5 concept×contrat (garantie centrale vs mention), avec preuves
- **[Qualité du routage](qualite-routage.html)** — métriques de précision : contrats, périmètre, sources, statut ; erreurs par famille
- **[Planificateur de recherche](planificateur.html)** — question → plan (concept, synonymes, contrats, catégories, notices)
- **[Index conceptuel](concepts.html)** — concepts métier reliant synonymes, contrats, catégories, sources
- **[Détecteur de couverture](couverture-recherche.html)** — présent / absent de la base / à vérifier en notice
- **[Comparateur thématique](comparateur.html)** — un sujet, tous les contrats côte à côte, sourcé
- **[Divergences inter-contrats](divergences.html)** — où les contrats diffèrent sur un chiffre (âge, délais) — signal à vérifier, jamais une contradiction
- **[Audit de traçabilité](tracabilite.html)** — par contrat : quelle part est pleinement sourcée (notice + page), et la liste de ce qui est à vérifier
- **[Graphe de preuves](preuves.html)** — chaque élément citable (id, source, page, concepts)
- **[Méthode & assembleur](methode-question-complexe.html)** — 5 parcours + structure de réponse sécurisée
- **[Hiérarchie documentaire](hierarchie.html)** — ordre : contrat → notice → docs AXA → réglementation → réponse
- **[Moteur choix des sources](choix-sources.html)** — quel document, quel ordre, quand s'arrêter, quand ne pas conclure
- **[Sources officielles](sources-officielles.html)** — autorités publiques (Légifrance, BOFiP, Ameli…) par concept
- **[Détecteur de réglementation](reglementation.html)** — signale une matière évolutive + autorités à consulter
- **[Surveillance documentaire](surveillance.html)** — dater / alerter / préparer (jamais de mise à jour auto)
- **[Connaissances dynamiques](connaissances-dynamiques.html)** — chaîne de validation prête (jamais automatique)
- **[Matrices documentaires](matrices.html)** — contrats × catégories, concepts × contrats (HTML/MD/JSON/CSV)
- **[Graphe documentaire](graphe.html)** — nœuds & relations dérivées (contrats, concepts, éléments, autorités)
- **[Rapport de maturité](maturite.html)** — capacités documentaires, réglementaires, de preuve, de couverture
- **[Jeux de tests](tests.html)** — ≥ 50 questions de contrôle + parcours attendus

## Formats machine
- [niveaux-competence.json](niveaux-competence.json) · [concepts.json](concepts.json) · [planificateur.json](planificateur.json) · [couverture-recherche.json](couverture-recherche.json) · [preuves.json](preuves.json) · [tests.json](tests.json)