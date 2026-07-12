# Cartographie Gabriel AXA (générée par generate_map.py — ne pas éditer à la main)

## Workflows → agents (branche cible : agents/proposals via _agents-run.yml ; jamais de merge auto)
- `_agents-run.yml` → agent=required mode=required cron=manuel
- `agents-concepts.yml` → agent=concepts mode=agent cron=37 6 * * 4
- `agents-coordinator.yml` → agent=— mode=coordinator cron=9 8 * * *
- `agents-corpus-explorer.yml` → agent=corpus-explorer mode=agent cron=37 */12 * * *
- `agents-coverage.yml` → agent=coverage-gaps mode=agent cron=29 4 * * 1,4
- `agents-extraction-llm.yml` → agent=extraction-llm mode=agent cron=47 3 * * 2,5
- `agents-extraction.yml` → agent=extraction-cg mode=agent cron=23 3 * * 1,3,5
- `agents-knowledge-builder.yml` → agent=knowledge-builder mode=agent cron=47 */12 * * *
- `agents-orchestrator.yml` → agent=— mode=cycle cron=17 */6 * * *
- `agents-quality.yml` → agent=quality mode=agent cron=17 2 * * *
- `agents-sources.yml` → agent=official-sources mode=agent cron=13 5 * * 1
- `agents-tests.yml` → agent=adversarial-tests mode=agent cron=41 4 * * 2,5
- `agents-ux.yml` → agent=ux-ai mode=agent cron=51 7 * * 6

## Agents → dépendances (imports réels)
- `agents/adversarial_tests.py` → safety_checks
- `agents/base.py` → provider_router, quota_manager, safety_checks
- `agents/concepts.py` → safety_checks
- `agents/corpus_explorer.py` → corpus_intel, orch, safety_checks
- `agents/coverage_gaps.py` → safety_checks
- `agents/extraction_cg.py` → safety_checks
- `agents/extraction_llm.py` → deduplicate, quota_manager, safety_checks
- `agents/inspector_evaluator.py` → inspector_bench, knowledge_graph, safety_checks
- `agents/knowledge_builder.py` → knowledge_build, knowledge_graph, knowledge_ops, knowledge_tasks, safety_checks
- `agents/knowledge_curator.py` → claude_enrichment, coverage_model, domain_adapter, environment_ingest, inspector_projection, knowledge_compare, knowledge_graph, knowledge_ingest, knowledge_manager, knowledge_projection, knowledge_review, knowledge_tasks, safety_checks
- `agents/official_sources.py` → safety_checks
- `agents/quality.py` → safety_checks
- `agents/ux_ai.py` → safety_checks

## Moteurs génériques (noyau réutilisable Gabriel Virtuel) → dépendances
- `change_detect.py` → —
- `claude_harness.py` → coverage_model, knowledge_build, knowledge_graph, knowledge_tasks, safety_checks
- `commercial_kit.py` → inspector_advice, inspector_mono, knowledge_graph
- `corpus_intel.py` → —
- `coverage_model.py` → knowledge_graph
- `domain_adapter.py` → —
- `inspector_advice.py` → inspector_case, inspector_needs, knowledge_graph
- `inspector_bench.py` → inspector_case, inspector_mono, inspector_multi, inspector_needs, inspector_solution, knowledge_graph
- `inspector_case.py` → —
- `inspector_mono.py` → coverage_model, inspector_case, inspector_needs, knowledge_graph, knowledge_status
- `inspector_multi.py` → knowledge_graph
- `inspector_needs.py` → corpus_intel, inspector_case, knowledge_graph
- `inspector_projection.py` → inspector_mono, inspector_multi, knowledge_graph
- `inspector_solution.py` → inspector_case, inspector_needs
- `knowledge_build.py` → knowledge_graph
- `knowledge_compare.py` → knowledge_graph
- `knowledge_graph.py` → —
- `knowledge_manager.py` → —
- `knowledge_ops.py` → knowledge_graph
- `knowledge_projection.py` → coverage_model, knowledge_graph
- `knowledge_review.py` → knowledge_graph
- `knowledge_status.py` → —
- `knowledge_tasks.py` → coverage_model, knowledge_graph, knowledge_ops
- `orch.py` → safety_checks, validate_proposal

## Adaptateur & contenu AXA
- `domains/axa.py` (adaptateur), `agent-work/enrichment/*.json` (sémantique/métier/expérience étiquetées),
  `config/*.json`, masters `ia/` + `data/AXA/` (lecture seule pour les agents).

## Artefacts persistants (restaurés depuis agents/proposals — voir restore_state.PERSISTENT)
- `agent-work/extraction/pending`
- `agent-work/extraction/reviewed`
- `agent-work/extraction/rejected`
- `agent-work/extraction/memory.json`
- `agent-work/extraction/production_history.json`
- `agent-work/extraction/learning.json`
- `agent-work/official-sources/pending`
- `agent-work/official-sources/reviewed`
- `agent-work/official-sources/rejected`
- `agent-work/official-sources/changes`
- `agent-work/official-sources/snapshots`
- `agent-work/concepts/pending`
- `agent-work/concepts/reviewed`
- `agent-work/concepts/rejected`
- `agent-work/tests/pending`
- `agent-work/tests/reviewed`
- `agent-work/tests/rejected`
- `agent-work/tests/metrics_history.json`
- `agent-work/tests/last_metrics.json`
- `agent-work/ux-ai/pending`
- `agent-work/ux-ai/reviewed`
- `agent-work/ux-ai/rejected`
- `agent-work/exploration/coverage_map.json`
- `agent-work/exploration/tasks.json`
- `agent-work/corpus-explorer/pending`
- `agent-work/corpus-explorer/reviewed`
- `agent-work/corpus-explorer/rejected`
- `agent-work/knowledge/graph.json`
- `agent-work/knowledge/tasks.json`
- `agent-work/knowledge/cost_ledger.json`
- `agent-work/knowledge/coverage.json`
- `agent-work/knowledge/projection`
- `agent-work/knowledge/review.json`
- `agent-work/knowledge/manager.json`
- `agent-work/knowledge/comparisons.json`
- `agent-work/knowledge/inspector`
- `agent-work/quality/reports`
- `agent-work/quality/incidents`
- `agent-work/coordinator`
- `agent-work/runs/manifests`
- `agent-work/runs/provider_metrics.json`
- `agent-work/runs/provider_scores.json`
- `agent-work/runs/benchmark.json`
- `agent-work/orchestrator/task_queue.json`
- `agent-work/orchestrator/provider_state.json`
- `agent-work/orchestrator/cycle_summary.json`
- `agent-work/orchestrator/cycles`
- `agent-work/orchestrator/idempotency.json`
- `agent-work/orchestrator/model_discovery.json`
- `agent-work/backlog/completed.json`
- `agent-work/backlog/blocked.json`
- `agent-work/scripts`
- `agent-work/config`
- `agent-work/schemas`
- `agent-work/README.md`

## Chaîne de production
```
masters + notices PDF
  → domains/axa (adaptateur) → knowledge_ingest + environment_ingest + claude_enrichment (étiqueté)
  → knowledge_graph (L1 preuves / L2 entités / L3 relations / L4 compréhension + statuts)
  → coverage_model (profondeur) → knowledge_tasks (backlog vivant) → knowledge-builder (LLM, gaté)
  → inspector_* (fiches, multi, cas, avis, kit) + knowledge_review/manager/compare
  → scripts/build_inspector_ia.py → ia/inspecteur/ (Vue IA publique, lecture seule)
```
