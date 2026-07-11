# Mission finale — Audit d'architecture (Phase 1) + journal de progression

## 1. Cartographie de l'existant

**Moteurs génériques** (domain-agnostiques, `scripts/`) : `knowledge_graph` (graphe 4 couches),
`coverage_model` (profondeur), `knowledge_ops` (passes déterministes + CostLedger), `knowledge_tasks`
(backlog vivant), `knowledge_build` (L3/L4, LLM injecté), `knowledge_ingest` + `environment_ingest`
(alimentation), `corpus_intel` (cartographie/zonage), `domain_adapter` (interface), `orch`/`orchestrator`/
`orchestrator_cycle` (orchestration), `provider_router`/`quota_manager` (routage/coût), `validate_*`/
`safety_checks` (garde-fous), `deduplicate`, `select_task`, `restore_state`.

**Adaptateur** : `domains/axa.py` (seul domaine). **Agents** : déterministes (quality, coverage-gaps,
knowledge-curator, coordinator, official-sources, adversarial-tests, ux-ai) ; LLM (extraction-llm,
corpus-explorer, knowledge-builder, concepts). **Schémas** : proposal, knowledge_node, backlog,
run-manifest. **Workflows** : orchestrateur (cycle) + 1 par agent. **Tests** : 174 verts.

## 2. Sources de vérité & redondances (à surveiller / rationaliser)

| Sujet | Stores actuels | Diagnostic |
|---|---|---|
| « Ce qu'on connaît » | `exploration/coverage_map.json` (zones, corpus-explorer) **et** `knowledge/graph.json`+`coverage_model` (profondeur, curateur) | **Deux vues** : coverage_map = cache d'exploration par zones ; graphe = vérité sémantique. **Le graphe est la source canonique.** coverage_map reste un cache amont (OK, mais à documenter comme tel). |
| Backlogs de travail | `exploration/tasks.json` (corpus-explorer) **et** `knowledge/tasks.json` (curateur) **et** `orchestrator/task_queue.json` (exécutable) | task_queue = **file d'exécution** (autorité orchestrateur). Les 2 backlogs = découverte typée. **Rationaliser** : le backlog de connaissance (`knowledge/tasks.json`) devient le backlog typé unique ; celui de corpus-explorer reste spécifique à l'exploration. |
| Preuves | proposals `extraction/pending` → projetées en L1 par `knowledge_ingest` | Cohérent (le graphe est dérivé, les propositions restent la source de revue). |

## 3. Risques identifiés

- **Clobber `task_queue.json`** : écrit par le cycle (mémoire→sauvegarde fin) ET par corpus-explorer. **Mitigé** par `concurrency: agents-proposals` (sérialise tous les workflows d'agents). Documenté ; ne jamais écrire la file hors de ce verrou.
- **Retraitement inutile** : maîtrisé (hash de zone, `needs_exploration`, garde « déjà relié/expliqué »). À étendre : classification fine des changements (Phase 7).
- **Confusion contractuel/externe** : **maîtrisée** — domaines séparés (`axa-contrat` vs `fiscalite`/`reglementation`), reliés uniquement par arêtes `governed_by`. À préserver absolument.
- **Schéma du graphe non ENFORCÉ** : `knowledge_node.schema.json` existe mais aucun validateur ne l'applique aux nœuds réels. → **Phase 2**.
- **Couches de champ incomplètes** : les nœuds ne portent pas encore `validations/ambiguities/risks/version` de façon systématique ; les arêtes pas de `sens`/`validation_required`. → **Phase 2**.

## 4. Capacités manquantes (feuille de mission)

Projection IA lecture seule (Ph.9), reviewer multi-niveaux (Ph.10), manager stratégique (Ph.11),
classification de changements (Ph.7), comparaison/contradictions avancées (Ph.8), environnement réseau
vivant (Ph.6), provider `claude-assisted-test` + harnais (Ph.14), campagne (Ph.15).

## 5. Décisions d'audit (prudentes, documentées)

1. **Le graphe est la source de vérité canonique** de la connaissance ; coverage_map et les backlogs sont des projections/caches amont. On ne fusionne pas brutalement (risque de régression) : on documente et on fait converger.
2. **Enforcement de schéma progressif** : ajouter un validateur de graphe + migration idempotente (Phase 2) sans casser l'existant (champs additifs, valeurs par défaut).
3. **Réutiliser official-sources** pour le réseau (Phase 6), pas de second système de veille.
4. **Provider `claude-assisted-test`** = mode explicite, étiqueté `simulation_assistee_par_claude`, jamais dans les schedules de production (Phase 14).

---

## Journal de progression (par phase)

- **Phase 1 — Audit** : ✅ (ce document).
- **Phase 2 — Modèle stabilisé** : ✅ nœuds portent `version/validations/ambiguities/risks` ; arêtes portent `directed`/`validation_required` (les relations interprétées LLM requièrent revue, les liens structurels `explains` non) ; `validate_node/edge/graph` + `migrate()` idempotente ; migration branchée dans le curateur + contrôle de schéma observable. Schéma `knowledge_node.schema.json` complété. Live : graphe 140 L1 / 221 L2 / 197 L3, schéma OK. 181 tests.
- **Phase 3 — Couverture sémantique & profondeur explicable** : ✅ `coverage_model` étendu — `category_presence` (couverture par catégorie), `quality_rates` (preuve/non-relié/incertitude/contradiction), `depth_counts` (L1-L4), et `explain()` qui dit POURQUOI un axe est faible et QUEL travail l'améliore. `expected_categories()` sur les adaptateurs. Le curateur écrit `knowledge/coverage.json` (rapport explicable par sujet). Live Avizen : semantic 0.385 (5/13 catégories), proof 0.78, isolées 0.41, L1/L2/L3/L4=21/27/26/0 → recommande extraire/relier/expliquer. 186 tests.
