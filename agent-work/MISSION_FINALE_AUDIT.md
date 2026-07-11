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
- **Phase 9 — Projection IA lecture seule** : ✅ `knowledge_projection.py` — vue par sujet DÉRIVÉE du graphe (synthèse, connaissances par catégorie, relations, environnement, compréhension, preuves, incertitudes, fraîcheur), **couches séparées**, provenance conservée, `validation_required` porté, reconstructible (empreinte du graphe), versionnée. Isolée sous `agent-work/knowledge/projection/` — **produit/masters intacts**. Branchée au curateur. Live : 9 projections, Avizen 5 catégories / 26 liens environnement / 21 preuves / 6 incertitudes. 191 tests. (Faite AVANT phase 4-8 car déterministe, sûre, à forte valeur.)
- **Phase 10 — Reviewer hiérarchisé** : ✅ `knowledge_review.py` — 4 niveaux (N1 structure, N2 sémantique, N3 second modèle sur SENSIBLE, N4 humain). Escalade auto/model/human ; sensibilité = exclusions/plafonds/conditions/montants (regex €/%). Réduit fortement la revue humaine. Live AXA : 196 items → 24% auto / 47% second-modèle / **28% humain** (le sensible/incertain). `knowledge/review.json`.
- **Phase 11 — Manager stratégique** : ✅ `knowledge_manager.py` — lit couverture/backlog/coût/scores fournisseurs, produit des recommandations VÉRIFIABLES (approfondir sujet faible, prioriser type dominant, router vers meilleur fournisseur, lacune persistante). Ne modifie JAMAIS la connaissance. Live : cible « Ma Protection Accident » (depth 0.61), type dominant `expliquer`. `knowledge/manager.json`. 197 tests.
- **Phase 14 — Mode `simulation_assistee_par_claude`** : ✅ provider de test `claude-assisted-test` (`providers/adapters.claude_assisted_chat` : rejoue des réponses enregistrées, 0 réseau ; **inéligible sans la clé `AXA_CLAUDE_ASSISTED` → jamais en production**) + harnais reproductible `claude_harness.py` (prepare/apply). Le code prépare le contexte réel, Claude raisonne, les réponses passent par les MÊMES garde-fous (types de relation, aucune entité inventée) et alimentent le graphe, marquées `provenance='simulation_assistee_par_claude'` + `validation_required`. 5 tests.
- **Phase 15 — Campagne assistée** : ✅ (locale) 3 contrats, **+18 L3 / +8 L4**, profondeur Avizen 0.72→0.77, Avizen Pro 0.73→0.76, Entour'Age 0.68→0.71 ; 0 rejet, 26 arêtes en attente de revue. Rapport honnête `tests/claude_assisted/CAMPAIGN.md`. **SIMULÉ** (raisonnement Claude), jamais confondu avec de la production.
- **Phase 16 — Auto-critique (1er correctif)** : ✅ faiblesse identifiée — `build_understanding` fournissait les libellés voisins comme « preuves » ; corrigé pour fournir le **résumé + les citations propres de l'entité** (`_entity_evidence`). 202 tests.
- **Phase 8 — Comparaison & contradictions** : ✅ `knowledge_compare.py` — comparaison inter-contrats par catégorie (matrice + différences de COUVERTURE), classification PRUDENTE des tensions (`difference_normale` / `variante_ou_doublon` / `candidat_contradiction`). **Une différence n'est pas une contradiction** ; rien n'est affirmé (validation requise). Branché au curateur → `knowledge/comparisons.json`. Live : 2 différences de couverture, 2 candidats de contradiction.
- **Phase 7 — Détection de changements** : ✅ `change_detect.py` — classe `nouveau_document`/`identique`/`modification_mineure`/`modification_structurante` (hash fichier + évolution du zonage), invalidation CIBLÉE (`zones_to_invalidate`) + tâches ciblées (`reexaminer_zone`/`marquer_obsolete`) ; un doc identique ne crée AUCUNE tâche (pas de retraitement). Complète corpus-explorer (qui suit déjà les zones par hash). 210 tests.
