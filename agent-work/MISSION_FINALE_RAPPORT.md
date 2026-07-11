# Mission finale — Rapport & critères de version (Phase 17)

Version : **v2.9.0** (plateforme autonome de construction de connaissances). Ce rapport est HONNÊTE :
il distingue ce qui fonctionne réellement, ce qui est simulé, et ce qui dépend encore d'une action humaine.

## Architecture finale (résumé)

- **Moteur générique** (domain-agnostique) : `knowledge_graph` (4 couches, provenance/fraîcheur/validation),
  `coverage_model` (profondeur + explicabilité), `knowledge_ops`/`knowledge_tasks` (passes déterministes +
  backlog vivant), `knowledge_build` (L3/L4, LLM injecté), `knowledge_ingest`/`environment_ingest`
  (alimentation), `knowledge_projection` (vue IA lecture seule), `knowledge_review` (revue hiérarchisée),
  `knowledge_manager` (recommandations), `knowledge_compare` (comparaison/contradictions),
  `change_detect` (changements), `corpus_intel` (cartographie), `provider_router`/`quota_manager` (routage/coût).
- **Adaptateur AXA** : `domains/axa.py` (le seul spécifique ; ajouter un adaptateur = nouveau domaine).
- **Agents** : déterministes (knowledge-curator, coverage-gaps, quality, coordinator, official-sources…),
  LLM (extraction-llm, corpus-explorer, knowledge-builder). Le curateur orchestre toutes les passes
  déterministes en un seul run 0-token dans le cycle.
- **Schémas** : `knowledge_node.schema.json` (complété), `proposal.schema.json`.
- **Mémoires/artefacts** (sous `agent-work/knowledge/`) : `graph.json` (source de vérité), `coverage.json`,
  `tasks.json` (backlog), `comparisons.json`, `review.json`, `manager.json`, `cost_ledger.json`,
  `projection/` (vue IA). Restaurés depuis `agents/proposals`, code depuis `main`.
- **Routines** : orchestrateur (6 h, central) + workflows par agent (12 h, sources/quality/…), concurrency
  `agents-proposals` (jamais deux en parallèle), timeout, gate `AGENTS_ENABLED`.

## Métriques (campagne locale, corpus AXA réel)

| | Déterministe (0 token, réel) | + assisté Claude (simulé, étiqueté) |
|---|---|---|
| L1 preuves | 140 | 140 |
| L2 entités | 221 | 221 |
| L3 relations | 197 (environnement `governed_by`) | +18 internes (excludes/comparable/…) |
| L4 compréhension | 0 | +8 explications |
| Profondeur moy. | 0.69 | Avizen 0.72→0.77, Avizen Pro →0.76, Entour'Age →0.71 |
| Domaines | axa-contrat / fiscalite / reglementation (séparés) | idem |
| Revue | 24 % auto / 47 % second-modèle / 28 % humain | idem |

## Critères de version finale — état réel

| Critère | État | Preuve |
|---|---|---|
| corpus ajouté → détecté | ✅ | corpus-explorer (file_hash) + `change_detect` |
| cartographie créée | ✅ | corpus-explorer + `coverage_map` |
| zones suivies par hash | ✅ | `needs_exploration` |
| couverture mesurée | ✅ | `coverage.json` (6 axes + catégories) |
| profondeur mesurée | ✅ | `depth_score` par sujet |
| tâches générées | ✅ | `tasks.json` (backlog vivant, 17) |
| tâches exécutées | ✅ (extraction hist.) / ✅ via harnais / ⏳ live LLM | extraction-llm historique ; knowledge-builder simulé |
| L1/L2 produites | ✅ RÉEL | 140 / 221 déterministes |
| L3 relations | ✅ environnement RÉEL (197) ; internes ✅ simulé / ⏳ live | env déterministe ; internes via LLM |
| L4 compréhension | ⚠️ **SIMULÉ** (8) ; ⏳ **live requiert clé LLM** | harnais Claude ; production = Gemini |
| environnement relié | ✅ RÉEL | 197 `governed_by`, domaines séparés |
| fraîcheur suivie | ✅ | TTL 365j sur nœuds environnement |
| changements détectés | ✅ | `change_detect` (4 types + invalidation ciblée) |
| contradictions signalées | ✅ (candidats prudents) | `comparisons.json` |
| comparaisons produites | ✅ | `comparisons.json` (2 différences) |
| projection IA générée | ✅ RÉEL | 9 projections, couches séparées |
| revue hiérarchisée | ✅ | `review.json` (28 % humain) |
| routine autonome définie | ✅ | workflows + schedules cohérents |
| résilience testée | ✅ | sauvegardes incrémentales + restore_state + tests |
| reprise testée | ✅ | `needs_exploration` + réconciliation backlog + tests |
| absence de doublons | ✅ | identités canoniques + tests dédup |
| aucun secret exposé | ✅ | détection true/false, redact_secrets |
| aucun usage payant | ✅ | allow_paid_usage=false, 0 provider payant |
| produit intact / masters intacts | ✅ | tout écrit sous `agent-work/` |
| tests complets verts | ✅ | **210 tests** |
| campagne quasi réelle documentée | ✅ (assistée, étiquetée) | `tests/claude_assisted/CAMPAIGN.md` |
| limites restantes explicites | ✅ | ci-dessous |

## Ce qui fonctionne réellement (0 token, vérifié)
Ingestion L1/L2 (196 entités, 140 preuves sourcées), ancrage environnement L3 (197 arêtes, domaines
séparés), couverture/profondeur explicable, backlog vivant, comparaison, détection de changement, revue
hiérarchisée, manager, projection IA lecture seule. Le tout additif, produit intact, 210 tests verts.

## Ce qui est SIMULÉ (raisonnement Claude, étiqueté `simulation_assistee_par_claude`)
Le contenu sémantique **L3 internes** (relations entre clauses) et **L4** (explications). Produit via le
harnais, marqué, en attente de revue. **Ce n'est PAS une sortie d'API autonome.**

## Ce qui dépend encore d'une action humaine / n'a pas pu être testé ici
1. **Run LLM de production** (Gemini) pour peupler L3-internes/L4 réellement : nécessite la clé
   `GEMINI_API_KEY` + déclencher `agents-knowledge-builder` (je n'ai pas de clé ; jamais de dépense).
2. **Environnement réseau vivant** (Phase 6 live) : la couche déterministe est faite ; la fraîcheur RÉELLE
   des sources officielles passe par l'agent `official-sources` (réseau), à déclencher en CI.
3. **Revue humaine** des 26 arêtes simulées + des propositions sensibles (par conception).
4. **Merge** de la PR `agents/proposals` (jamais automatique).

## Limites restantes explicites
- L4/L3-internes en production non encore exercés avec une vraie clé (simulés localement).
- La cartographie corpus-explorer reste heuristique (mots-clés).
- La détection de contradiction est prudente (candidats, jamais d'affirmation).
- `knowledge_node.schema.json` est validé par un contrôleur interne, pas par un validateur JSON-Schema strict.
