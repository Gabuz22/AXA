# GABRIEL AXA v4.0.0 — Document de transmission

> Pour : moi dans six mois, un développeur qui découvre le projet, une IA qui doit le comprendre.
> Compléments : `CARTOGRAPHIE.md` (générée : `python agent-work/scripts/generate_map.py`),
> `ARCHITECTURE_KNOWLEDGE_PLATFORM.md`, `INSPECTOR_MISSION.md`, `MISSION_FINALE_RAPPORT.md`,
> `tests/claude_assisted/CAMPAIGN.md`. État : **267 tests verts, bench Inspecteur 0.97, chaîne validée**.

## 1. Ce qu'est devenu ce projet

Gabriel AXA a commencé comme une base documentaire d'assurance. Il est devenu **le premier domaine
d'application d'une plateforme générique** de construction de connaissances et de raisonnement :

```
masters (ia/, data/AXA/)  ──lecture seule──▶  adaptateur (domains/axa.py)
   ▼
knowledge_graph — L1 preuves (immuables, sourcées) · L2 entités · L3 relations · L4 compréhension
   provenance + fraîcheur + confiance + STATUTS (validated / derived / pending / simulated_claude / stale…)
   ▼                                             ▼
coverage_model (profondeur explicable)      knowledge_review/manager/compare (passes déterministes, 0 token)
   ▼
knowledge_tasks (backlog VIVANT pending↔resolved)  ──▶  knowledge-builder (LLM gaté, budget, fail-open)
   ▼
inspector_* : fiche mono · comparaison multi · cas client (statuts stricts) · décomposition par RISQUE ·
avis d'inspecteur (priorisation, audit existant, pièges, objections) · kit de RDV · bibliothèque d'EXPÉRIENCE
   ▼
scripts/build_inspector_ia.py  ──▶  ia/inspecteur/ (Vue IA publique, dérivée, versionnée, lecture seule)
```

Boucle autonome : GitHub Actions (orchestrateur central 6 h + agents gatés `AGENTS_ENABLED`), état persistant
sur la branche `agents/proposals` (code TOUJOURS depuis main via `restore_state.py`), commit confiné à
`agent-work/` (`validate_scope.py`, fail-closed), **jamais de merge auto**, coût **zéro** (`allow_paid_usage=false`).

## 2. Pourquoi chaque composant existe (l'essentiel)

| Composant | Pourquoi | Utilisé par |
|---|---|---|
| `knowledge_graph` | source de vérité unique en 4 couches, dédup canonique, évidence immuable | tout |
| `knowledge_status` | une connaissance n'est JAMAIS « validée » parce qu'elle existe ; l'exposé étiquette | projections, fiches |
| `coverage_model` | mesurer la COMPRÉHENSION (pas les pages) et EXPLIQUER quoi améliorer | curator, manager, bench |
| `knowledge_tasks` | le système découvre son propre travail (backlog auto-réparant) | curator→builder |
| `domain_adapter` + `domains/axa` | domaine = adaptateur ; le moteur ne connaît pas AXA | ingestion, builds |
| `enrichment/*.json` | la sémantique/le métier/l'EXPÉRIENCE raisonnés par Claude, **curés, diff-ables, étiquetés** | advise, fiches, kit |
| `inspector_advice` | « que ferais-tu à ma place ? » : priorisation par profil (faits seuls), audit existant, leçons | kit, IA externes |
| `claude_harness` + provider `claude-assisted-test` | tester les chemins LLM sans API, jamais en prod (clé absente) | dev/tests |
| `orchestrator(.py/_cycle)` + `orch` | statut MÉTIER (jamais le seul exit code), file, routage explicable, budgets | CI |

Points de fragilité connus (documentés, testés) : quoting git des noms non-ASCII (corrigé `-z`+UTF-8,
slugs ASCII partout) ; `KG._norm` NE strippe PAS les accents (matching → `corpus_intel.norm`) ;
rebuild produit : lancer `build_inspector_ia.py` APRÈS `build_ia.py` et vérifier que le commit capture le rebuild.

## 3. Audit de simplification (fait ; reste assumé)

- **Legacy conservés volontairement** (désactivés, zéro risque, valeur d'historique) : `extraction_cg`
  (remplacé par extraction-llm), `ux_ai`/`concepts` (manuels). Les supprimer n'apporte rien ; ils ne migrent PAS.
- **Doublons convergés** : coverage_map (cache d'exploration) vs graphe → documenté : le graphe est canonique.
  Les 2 backlogs (exploration/tasks vs knowledge/tasks) : knowledge/tasks est le backlog de référence.
- **Non fusionné exprès** : `inspector_*` en petits modules purs = testables, composables ; une fusion
  n'apporterait que de l'opacité.

## 4. GÉNÉRICITÉ — inventaire de migration vers Gabriel Virtuel

**Noyau générique (migrer tel quel, dépendances ↦ ordre conseillé)** :
1. `knowledge_graph` + `knowledge_status` + schéma (aucune dépendance ; difficulté faible) — **lot 1**
2. `coverage_model`, `knowledge_ops/tasks/review/manager/compare`, `change_detect` (dép : graphe) — **lot 1**
3. `domain_adapter` (interface) + patron `enrichment/` + `experience_library` (schéma situation→leçons) — **lot 1**
4. `corpus_intel` (cartographie/zonage générique) + `knowledge_ingest`/`environment_ingest` (génériques à 90 % :
   extraire les 2-3 constantes AXA) — **lot 2**
5. `orch` + `orchestrator*` + `provider_router`/`quota_manager` + workflows patrons (`_agents-run`, gates,
   concurrency, restore_state, validate_scope) — **lot 2** (difficulté moyenne : chemins/branche à paramétrer)
6. `inspector_case/needs/solution/advice` + `commercial_kit` (le RAISONNEMENT est générique : profils,
   priorisation, audit d'existant, kit ; seul le contenu métier est AXA) — **lot 3**
7. `claude_harness` + provider claude-assisted + politique d'étiquetage — **lot 3**
8. `inspector_projection`/`knowledge_projection` + patron `build_*_ia.py` (Vue IA dérivée) — **lot 3**

**Adaptateur métier (à réécrire par domaine)** : `domains/axa.py`, `enrichment/*.json` (contenu),
`config/agents.json` (sélection d'agents), catégories attendues, label_rules.

**Spécifique AXA (ne migre pas)** : masters `ia/`+`data/AXA/`, app conseiller, `build_ia.py`,
extraction_llm (garde anti-hallucination liée aux notices — le PATRON migre, pas le code tel quel), legacy.

## 5. Plan d'industrialisation Gabriel Virtuel (lots)

| Lot | Contenu | Dépend | Risque | Estim. | Bénéfice |
|---|---|---|---|---|---|
| **GV-0 socle** | repo noyau : graphe+statuts+couverture+tasks+adapter-interface+tests portés | — | faible | 1 session | fondation testée immédiatement |
| **GV-1 agents** | orch/orchestrateur/routeur/workflows patrons + curator générique | GV-0 | moyen (CI, secrets) | 1-2 sessions | autonomie PC éteint |
| **GV-2 raisonnement** | inspector_* génériques + expérience + harness Claude | GV-0 | faible | 1 session | avis/kit pour tout domaine |
| **GV-3 1er domaine** | adaptateur « journal personnel » (ou droit) : documents(), known_terms(), enrichment curé | GV-0..2 | faible | 1 session | preuve de généricité réelle |
| **GV-4 Vue IA** | build de projection dérivée + guide IA par domaine | GV-2,3 | faible | 0,5 | exposition |
| **GV-5 AXA-as-adapter** | brancher AXA comme domaine N (pas le premier !) en réutilisant enrichment existant | GV-3 | faible | 0,5 | continuité |

Règle d'or de migration : **porter les tests avec le code** (ils encodent les leçons) ; ne JAMAIS copier
un module sans son test.

## 6. « Si je recommençais aujourd'hui » — réponse honnête

**Je referais différemment :**
1. **Le graphe + statuts dès le jour 1.** coverage_map/backlogs multiples ont convergé tard ; des vérités
   parallèles = la principale dette de ce projet.
2. **Provenance/étiquetage dès le jour 1** (le pattern `simulated_claude` a tout simplifié quand il est arrivé).
3. **Slugs ASCII + git `-z` dès le jour 1** — le bug de périmètre a coûté un cycle complet d'autonomie.
4. **Un orchestrateur central d'abord, les workflows par agent ensuite** (l'inverse a créé 13 workflows dont
   plusieurs quasi redondants — assumés maintenant, mais GV n'en aura pas besoin).
5. **Le patron « enrichment curé » plus tôt** : des fichiers JSON diff-ables raisonnés par Claude, revus via
   git, valent mieux que des appels LLM précoces.

**Je garderais absolument :** déterministe d'abord (0 token pour tout ce qui peut l'être) ; domaine=adaptateur ;
fail-closed partout (scope, préflight, coût nul) ; statut métier ≠ exit code ; l'expérience comme donnée
(bibliothèque) ; la revue humaine comme invariant, pas comme option.

**Faut-il reconstruire avant de migrer ? NON.** Le noyau générique est propre, découplé et couvert par
267 tests. Reconstruire dans AXA serait du perfectionnisme ; la valeur est dans GV-0.

## 7. Actions humaines restantes (inchangées)
1. Runs API réels (`GEMINI_API_KEY` + Actions→agents-knowledge-builder / agents-sources).
2. Revue des interprétations étiquetées + PR `agents/proposals` (jamais de merge auto).
3. Décision d'exposer davantage la zone `/ia/inspecteur/` dans la navigation produit.

**Verdict : Gabriel AXA est une base mature. Les développements majeurs suivants appartiennent à Gabriel Virtuel.**
