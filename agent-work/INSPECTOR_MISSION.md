# Mission « Inspecteur fonction support » — audit + journal

## Phase 1 — Audit du point de vue de l'IA utilisatrice

**Ce qui existe et sert déjà l'IA :** projection mono-contrat (`knowledge/projection/<sujet>.json` :
garanties/exclusions/relations/environnement/compréhension/preuves/incertitudes) ; comparaison multi
(`comparisons.json` : matrice par catégorie + différences de couverture + candidats de contradiction) ;
graphe 4 couches sourcé ; couverture/profondeur ; revue hiérarchisée.

**Ce qui MANQUE pour raisonner comme un inspecteur :**
1. **Modèle de CAS CLIENT** — absent. Aucune structure faits/hypothèses/inconnues/besoins.
2. **Décomposition du besoin** — absent. Pas de cas → objectifs → risques → besoins → concepts → contrats.
3. **Fiche de raisonnement mono-contrat** — la projection liste, mais ne structure pas finalité / public /
   architecture / confusions / situations favorables·défavorables / ce qu'il faut pour juger un cas.
4. **Comparaison multi par MÉCANISME** — la comparaison actuelle est par catégorie/mots-clés, pas par
   mécanisme (définition, déclencheur, substituable/complémentaire/doublon/trou).
5. **Construction de solutions & arbitrages** — absent.
6. **Outils/protocoles pour IA** — absent (pas d'index d'outils, pas de schémas d'E/S, pas de guide IA).
7. **Banc d'essai métier + évaluateur** — absent.

**Écart graphe ↔ Vue IA produit :** la projection vit sous `agent-work/`, PAS dans la Vue IA du produit
(`/ia`). Exposer la projection Inspecteur au produit nécessite une validation humaine (Phase 19) : je
produis donc un **artefact dérivé isolé** sous `agent-work/knowledge/inspector/`, jamais dans les masters.

**Décisions (prudentes, génériques) :** les moteurs de raisonnement sont DÉTERMINISTES (assemblent des
échafaudages depuis le graphe) ; l'LLM/Claude ne comble que les vrais trous sémantiques. Tout distingue
faits / hypothèses / inconnues / clause / règle externe / interprétation. Rien n'affirme une éligibilité ;
tout cas incomplet reste conditionnel. Isolé du produit.

## Journal
- **Phase 1 — Audit** : ✅ (ce document).
- **Phase 2 — Modèle de cas client** : ✅ `inspector_case.py` (statuts confirmé/déclaré/déduit/hypothèse/inconnu/à_vérifier ; hypothèse jamais un fait ; besoins exprimés≠déduits ; validate/completeness).
- **Phase 3 — Décomposition du besoin** : ✅ `inspector_needs.py` (cas → besoins → contrats/garanties possibles → données nécessaires → arbitrages ; candidats prudents, jamais d'éligibilité).
- **Phase 4 — Raisonnement mono-contrat** : ✅ `inspector_mono.py` (`reasoning_sheet` : finalité/architecture/déclencheurs/conditions/exclusions/environnement/incertitudes ; `apply_case` : conclusion PROVISOIRE conditionnelle, confiance bornée par complétude, validation requise). Trous L4 signalés « à approfondir (LLM) ».
- **Phase 5 — Raisonnement multi-contrats** : ✅ `inspector_multi.py` (comparaison par mécanisme + classification substituables/complémentaires/doublon/non_comparables ; trous de couverture ; échoue proprement si aucun mécanisme partagé ; preuves par contrat, jamais mélangées).
- **Phases 6-7 — Solutions & arbitrage** : ✅ `inspector_solution.py` (`build_scenarios` : mono/multi/renforcé/existant, besoins couverts·non couverts, doublons, avantages/inconvénients ; `arbitrate` : meilleur PAR AXE, jamais absolu, compromis explicités). Aucun coût/fiscalité inventé ; validation requise.
- **Phases 9-10 — Projection Inspecteur & outils IA** : ✅ `inspector_projection.py` — fiches mono-contrat + comparaison + matrices (mécanisme→contrats, contrat→garanties/conditions/exclusions, concept→définitions par contrat) + `tools.json` (9 outils déclaratifs mappés aux moteurs) + `GUIDE_IA.md`. Branché au curateur → `knowledge/inspector/` (ISOLÉ du produit). Live : 9 fiches, 9 outils.
- **Phases 11-13 — Banc + évaluateur + boucle** : ✅ `inspector_bench.py` — banc mono/multi/cas + évaluateur DÉTERMINISTE (aucune invention [libellés vérifiés dans le graphe], pas de mélange, données manquantes signalées, distinction faits/hypothèses, « je ne sais pas » si rien ne correspond) + `diagnose` (échec→tâche typée). Live AXA : **score global 0.97** (mono 1.0 / multi 1.0 / cas 0.93).
- **Phase 16 — Agent inspector-evaluator** : ✅ déterministe, enregistré, exécute le banc, écrit `knowledge/inspector/bench_results.json`, suit les scores, crée des tâches correctives. Ne modifie jamais la connaissance.
- **Phases 17-18 — Agents solution-architect / multi-contract-reasoner** : ✅ livrés comme MOTEURS déterministes (`inspector_solution` / `inspector_multi`), exposés via `tools.json`. Un wrapper d'agent dédié est optionnel (les moteurs sont déjà exécutables et testés).
