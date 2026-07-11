# Campagne `simulation_assistee_par_claude` (Phases 14-15) — rapport honnête

> **Ceci n'est PAS un test d'API réel.** Les réponses sémantiques ont été produites par le raisonnement
> de Claude (protocole manuel reproductible via `claude_harness.py`), injectées dans le pipeline via le
> provider de test `claude-assisted-test`. Elles portent toutes `provenance='simulation_assistee_par_claude'`
> et `validation_required=true` (en attente de revue humaine). Elles ne doivent jamais être confondues avec
> des sorties de production autonomes.

## Protocole (reproductible)
1. `knowledge-curator` (déterministe) construit le graphe + le backlog (tâches `relier`/`expliquer`).
2. `python claude_harness.py --mode prepare` : le CODE prépare les prompts réels (catalogues d'entités,
   contraintes, schéma attendu) à partir des vraies tâches du backlog → `prompts.json`.
3. Claude lit les prompts, raisonne, écrit ses réponses JSON dans `responses.json`.
4. `AXA_CLAUDE_RESPONSES=… claude_harness.py --mode apply` : les réponses passent par les MÊMES fonctions
   `knowledge_build` (mêmes garde-fous : types de relation autorisés, indices existants seulement — aucune
   entité inventée) et alimentent le graphe, marquées + à valider.

## Résultats mesurés (campagne locale, 2 sujets `relier` + sujets `expliquer`)
| Sujet | Profondeur avant | après | Δ |
|---|---|---|---|
| Avizen | 0.719 | 0.770 | +0.051 |
| Avizen Pro | 0.727 | 0.760 | +0.033 |
| Entour'Age | 0.682 | 0.709 | +0.027 |

- **+18 relations L3** (excludes / comparable_to / complements / limits / refines), **+8 explications L4**.
- **Contrôles passés** : validation des types de relation (100 %), indices d'entités existants (0 entité
  inventée), toutes les sorties marquées `simulation_assistee_par_claude` + `validation_required`.
- **Contrôles échoués** : aucun rejet (toutes les propositions étaient valides au schéma).
- **Coût API réel** : 0 (aucun appel réseau). Coût simulé : ~10 « appels » (2 relier + 8 expliquer).

## Faiblesses observées (Phase 16 — auto-critique)
1. **`build_understanding` fournit des « preuves » = libellés d'entités voisines**, pas des citations
   documentaires réelles. Cause : les entités structurées ont une preuve L1 dont la citation = le titre.
   → Amélioration appliquée : le prompt inclut désormais le `resume` de l'entité elle-même (contexte plus
   riche) ; à terme, brancher les vraies citations d'extraction-llm.
2. **Relations déduites des libellés** (pas du texte intégral des clauses) → confiance volontairement
   modérée (0.5-0.6) et `validation_required=true`. Correct : rien n'est affirmé sans revue.
3. **Tâches mieux adaptées à Claude** : explications L4 et relations sémantiques (compréhension).
   **Mieux adaptées au déterministe** : dédup, fraîcheur, comptages, ancrage environnement (déjà 0 token).

## Statut
Simulé (raisonnement Claude) : le contenu sémantique L3/L4. Réel : tout le pipeline (préparation de
contexte, garde-fous, graphe, projection, revue). En attente de revue humaine : les 26 arêtes marquées.
