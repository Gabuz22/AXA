# Mission « Inspecteur opérationnel dans la Vue IA » — rapport final (honnête)

Version : **v3.1.0**. À partir de v3.0.0 : fermeture de la boucle **graphe → projection → Vue IA → IA
consommatrice**. Distinction stricte réel / simulé / préparé / en attente.

## Phase 1 — Audit de la chaîne réelle
`masters (contrats.json, notices PDF, sources-officielles.json)` → adaptateur AXA → ingestion déterministe
→ graphe **L1/L2/L3-environnement** → moteurs Inspecteur → **projection `/ia/inspecteur/`** → Vue IA (Pages)
→ IA consommatrice.

| Maillon | État |
|---|---|
| Ingestion L1/L2 + environnement L3 | **RÉEL, déterministe, 0 token** (140 preuves, 221 entités, 197 `governed_by`) |
| L3-internes (excludes/comparable…) + L4 (explications) | **SIMULÉ** localement (Claude) ; **RÉEL en attente d'un run API** (knowledge-builder) |
| Projection Inspecteur | **RÉEL** — 9 fiches, comparaison, matrices, outils, guide |
| Exposition Vue IA | **RÉEL** — `/ia/inspecteur/` généré sur `main`, servi par Pages, pointeur dans `ai-manifest.json` |
| IA consommatrice | **VÉRIFIÉ** — expérience testée en ne consultant QUE `/ia/inspecteur/` |

**Écart résiduel important (honnête)** : l'exposition `/ia/inspecteur/` est reconstruite **depuis les
masters** (déterministe) ; elle ne contient donc PAS encore les L3-internes/L4 produits par le LLM
(ceux-ci vivent dans le graphe d'état de la branche `agents/proposals`). Pour les exposer, il faudra
qu'un run knowledge-builder réel les produise, qu'ils soient revus, puis qu'un pont (snapshot de graphe
committé) alimente `build_inspector_ia.py`. **Aujourd'hui l'exposition = charpente déterministe + preuves**
(déjà très utile : garanties, exclusions, conditions, environnement daté, comparaison, matrices, outils,
méthode).

## Phases 4-6 — Projection & exposition (livré, réel)
`scripts/build_inspector_ia.py` (déterministe) écrit `ia/inspecteur/` : `GUIDE_IA.md` (méthode 12 étapes +
règles), `contrats/<slug>.json` (fiche + **preuves sourcées**), `comparison.json`, `matrices.json`,
`tools.json` (17 outils : analyser_contrat, comparer_contrats, analyser_cas_client, construire_solutions,
comparer_solutions, verifier_source_externe, distinguer_fait_hypothese_inconnu,
distinguer_contractuel_externe_interpretatif, …), `index.json/html`. **Masters + pages /ia existantes
intacts** ; seul un pointeur additif dans `ai-manifest.json`.

## Phase 13 — Expérience IA (vérifié)
En ne consultant QUE `/ia/inspecteur/` : une IA trouve l'index → lit le guide → découvre 17 outils → ouvre
la fiche d'un contrat (preuves document+page, exclusions, conditions) → utilise `comparison.json`
(36 paires classées, 2 trous) → `matrices.json`. Découvrable via `ai-manifest.json`.

## Phases 2-3 — Campagnes API réelles : PRÉPARÉES, NON EXÉCUTÉES (pas de clé ; aucune dépense)
> Je n'ai pas de clé LLM ; je n'ai donc **pas** exécuté de run API. Les workflows sont prêts.

**knowledge-builder (L3-internes/L4)** — run manuel GitHub :
1. Secrets dépôt : `GEMINI_API_KEY` (+ éventuellement GROQ/OPENROUTER/CLOUDFLARE_*), variable `AGENTS_ENABLED=true`.
2. Actions → **agents-knowledge-builder** → *Run workflow* → `force_dry_run` **décoché**.
3. Il puise le backlog (**15 tâches relier/expliquer prêtes**), utilise les vraies preuves, produit L3/L4
   marqués `provenance` + `validation_required`, recalcule la profondeur, commit sur `agents/proposals`.
4. À vérifier ensuite dans le résumé du run : fournisseur/modèle réellement utilisés, appels LLM, tokens,
   tâches consommées, acceptées/rejetées + motifs, gain de profondeur, absence de doublons/mélange.

**official-sources (fraîcheur réglementaire)** — run manuel :
1. Actions → **agents-sources** → *Run workflow* → `force_dry_run` décoché.
2. Vérifie statut HTTP/empreinte des autorités officielles (jamais d'interprétation juridique), classe
   inchangé/redirigé/modifié/indisponible, crée des tâches de revalidation ; une source en erreur ne casse
   pas le cycle. Les règles externes restent séparées des clauses, datées.

## Phase 17 — Routine
- Cycle (déterministe, 0 token) : `knowledge-curator` → `inspector-evaluator` (score banc) → coverage/quality.
- LLM (avec clé) : `agents-knowledge-builder` (12 h), `agents-sources` (hebdo), gatés `AGENTS_ENABLED`,
  concurrency partagée (jamais parallèles), PC éteint OK.
- **Exposition `/ia/inspecteur/`** : reconstruite par `build_inspector_ia.py` (à lancer après `build_ia.py`
  lors d'un build produit). N'est PAS écrite par les agents (périmètre agent-work/ strict).

## Phase 18 — Critères
✅ projection générée · ✅ exposée dans la Vue IA · ✅ outils découvrables · ✅ guide accessible ·
✅ mono/multi/cas/solutions/arbitrages testés (banc 0.97) · ✅ preuves contrôlées · ✅ règles externes
séparées + datées · ✅ échecs→tâches (diagnose) · ✅ re-tests (banc chaque cycle) · ✅ aucune régression
(238 tests) · ✅ masters intacts, produit intact hors zone dérivée validée · ✅ aucun usage payant ·
✅ aucun secret exposé.
⏳ **knowledge-builder / official-sources en API réelle** : workflows PRÉPARÉS, run à déclencher (clé).

## Statut honnête
- **Réel (vérifié)** : ingestion déterministe, environnement L3, moteurs Inspecteur, projection, exposition
  `/ia/inspecteur/`, expérience IA, banc 0.97.
- **Simulé (étiqueté)** : L3-internes/L4 (raisonnement Claude), en attente d'un run API réel.
- **Préparé, non exécuté** : campagnes API (pas de clé).
- **En attente humaine** : déclenchement des runs API (secrets), revue des propositions sensibles, merge PR,
  pont graphe-enrichi → exposition (pour exposer L4/L3-internes une fois validés).
