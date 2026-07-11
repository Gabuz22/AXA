# Mission « Inspecteur fonction support » — rapport final (honnête)

Version : **v3.0.0**. Ce rapport distingue ce qui est réellement validé, simulé, partiel ou en attente.

## Objectif atteint (dans son périmètre)
Une IA qui consulte la projection Inspecteur dispose d'un **environnement de raisonnement** (pas d'une
simple recherche) : fiches mono-contrat, comparaison multi par mécanisme, matrices, modèle de cas client,
décomposition du besoin, construction de solutions, arbitrage explicable, banc d'essai + évaluateur, et un
guide + des outils. Le tout **déterministe, 0 token, isolé du produit**, avec des garde-fous stricts.

## Les 4 familles de raisonnement — couvertes
| Famille | Moteur | Sortie |
|---|---|---|
| mono-contrat sans cas | `inspector_mono.reasoning_sheet` | fiche (finalité, architecture, déclencheurs, conditions, exclusions, environnement, incertitudes) |
| multi-contrats sans cas | `inspector_multi.compare` | paires classées (substituables/complémentaires/doublon/non_comparables) + trous |
| mono-contrat + cas | `inspector_mono.apply_case` | clauses pertinentes, conditions/exclusions à vérifier, données manquantes, conclusion PROVISOIRE |
| multi-contrats + cas | `inspector_needs` + `inspector_solution` | décomposition → scénarios → arbitrage par axe |

## Composants livrés
- **Modèle de cas client** (`inspector_case`) : statuts confirmé/déclaré/déduit/hypothèse/inconnu/à_vérifier ; une hypothèse n'est jamais un fait ; besoins exprimés ≠ déduits.
- **Décomposition du besoin** (`inspector_needs`), **mono** (`inspector_mono`), **multi** (`inspector_multi`), **solutions+arbitrage** (`inspector_solution`).
- **Projection Inspecteur + outils IA** (`inspector_projection` → `knowledge/inspector/` : fiches, comparaison, matrices, `tools.json`, `GUIDE_IA.md`).
- **Banc + évaluateur + boucle** (`inspector_bench`) et **agent** `inspector-evaluator` (dans le cycle).

## Métriques (déterministe, réel, sur le graphe AXA)
- Banc Inspecteur : **score global 0.97** (mono 1.0 / multi 1.0 / cas_mono 0.93 / cas_multi 1.0).
- Contrôles déterministes vérifiés : aucune invention (libellés vérifiés dans le graphe), pas de mélange
  de contrats, données manquantes signalées, conclusions conditionnelles, « je ne sais pas » si rien ne
  correspond, validation humaine signalée.
- **288 → 235 tests** au total (suite complète verte), 0 régression.

## Ce qui fonctionne réellement (vérifié, 0 token)
Toute la CHARPENTE de raisonnement : structure des fiches, comparaison par mécanisme, décomposition,
scénarios, arbitrage explicable, matrices, outils, guide, banc + évaluateur. Garde-fous stricts respectés.

## Limite structurante honnête (auto-critique)
Le **matching besoin↔contrat est déterministe (recoupement de termes)** : il a une bonne COUVERTURE
(recall) mais une PRÉCISION limitée — il propose des CANDIDATS larges (ex. un besoin « invalidité/accident »
peut recaler des contrats non pertinents). C'est **assumé et étiqueté** (« candidats à confirmer ») : la
précision sémantique (écarter un candidat, comprendre un mécanisme, expliciter un arbitrage chiffré)
relève de l'**IA consommatrice** (ou du `knowledge-builder` LLM), qui s'appuie sur les fiches, matrices et
preuves. Le bon partage : **déterministe = échafaudage + garde-fous ; LLM/IA = précision sémantique.**

## Simulé (raisonnement Claude, étiqueté) / en attente
- La couche L4 (explications) et les relations internes L3 restent **simulées** localement
  (`simulation_assistee_par_claude`) ou à produire en LLM de production — elles enrichissent les fiches.
- **Campagne API réelle (Phase 15)** : NON exécutée (pas de clé LLM disponible ; aucune dépense). À
  lancer via `agents-knowledge-builder` avec `GEMINI_API_KEY`.
- **Exposition à la Vue IA produit (Phase 19)** : la projection Inspecteur est un **artefact dérivé isolé**
  (`agent-work/knowledge/inspector/`). L'exposer dans `/ia` du produit exige une **validation humaine**
  (modification proche du produit) — non faite (règle 6). Le GUIDE_IA + tools.json sont prêts pour cette
  exposition le moment venu.

## Sécurité (respectée)
Aucun master modifié ; aucune donnée contractuelle intégrée sans revue ; aucun merge auto ; aucun secret
exposé ; aucun usage payant ; aucune recommandation présentée comme certaine ; règles externes datées ;
preuves conservées par contrat ; faits/hypothèses/inconnues séparés ; sorties sensibles en revue humaine.

## Actions humaines restantes
1. Lancer une campagne LLM de production (clé) pour peupler L3-internes/L4 réellement.
2. Décider de l'exposition de la projection Inspecteur à la Vue IA produit (validation).
3. Revoir les candidats/propositions sensibles et merger la PR `agents/proposals`.
