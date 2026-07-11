# Mission « Fermeture de boucle Inspecteur » — rapport final (honnête)

Version : **v3.2.0** (à partir de v3.1.0). Objet : statuts de validation + pont contrôlé graphe→projection
+ vérification du lien public réel. Distinction stricte réel / simulé / préparé / en attente.

## Phase 1 — Audit des données exposées (matrice)
| Connaissance | Masters | Graphe déterministe | Statut | Exposée /ia/inspecteur |
|---|---|---|---|---|
| L1 preuves (doc/page/citation) | oui | 140 | `validated` (source master) | **oui** |
| L2 entités (garanties/exclusions/…) | oui | 221 | `validated` | **oui** |
| L3 environnement (governed_by) | dérivé | 197 | `derived_deterministic` | **oui (étiqueté)** |
| L3 internes (excludes/comparable) | non | 0 (branche/LLM) | `pending_review`/`simulated_claude` | non (attendu run LLM) |
| L4 explications | non | 0 (branche/LLM) | idem | non |
| Fraîcheur réglementaire réelle | — | TTL statique | `stale` si dépassé | signalée |

Écart : l'exposition = **charpente déterministe validée + preuves** ; l'interprété/LLM reste hors exposition
tant qu'il n'est pas produit (run API) et revu.

## Phase 4 — Statuts de validation (`knowledge_status.py`, réel)
Statut DÉTERMINISTE par nœud/arête : `validated` (masters), `derived_deterministic` (dérivation),
`pending_review` (LLM/propositions), `simulated_claude`, `stale`, `contradictory`, `uncertain`, `rejected`.
Politique : **seuls `validated` + `derived_deterministic` exposables comme vérité** ; le reste visible
UNIQUEMENT étiqueté, jamais comme clause/règle certaine.

## Phase 5-6 — Pont contrôlé + projection enrichie (réel)
Chaque fiche `/ia/inspecteur/contrats/<slug>.json` porte un bloc `validation` en BLOCS SÉPARÉS :
`validated_knowledge`, `derived_relations`, `pending_interpretations`, `simulated_claude`,
`uncertainties`, `stale`, `contradictory`, `human_review_required`. Live : Avizen = 27 validated + 26
derived_relations, **0 simulé/pending** (build déterministe).

## Phase 7 — Vues cas clients (réel, exposées)
`/ia/inspecteur/cas-clients/` : `case_schema.json`, `case_reasoning_protocol.json`, `arbitration_axes.json`,
`missing_information_protocol.json`, `solution_scenarios.example.json` (synthétique).

## Phase 8 — Test du lien public (RÉEL, vérifié en ligne)
`https://gabuz22.github.io/AXA/ia/inspecteur/` accessible. `index.json` valide (9 contrats). Fiche
`contrats/avizen.json` valide : **21 preuves sourcées** (Avizen…Notice…pdf, pages 8–27), **5 exclusions**.
(Le déploiement Pages reflète le commit précédent ; la version avec blocs de validation redéploie au
prochain build Pages.)

## Phases 9-11 — Campagnes sur les artefacts EXPOSÉS uniquement (réel)
- MONO : **9/9** fiches exploitables (preuves + exclusions + statut `validated`).
- MULTI : comparaison **36 paires classées** (substituables/complémentaires/doublon/non_comparables),
  **2 trous** ; preuves conservées par contrat.
- CAS : **4/4** artefacts présents (schéma + 3 protocoles).
- SÛRETÉ : **0** élément simulé exposé comme vérité (build déterministe).

## Phases 2-3 — API réelle : PRÉPARÉES, NON EXÉCUTÉES (pas de clé ; aucune dépense)
Inchangé depuis v3.1.0 : workflows `agents-knowledge-builder` (15 tâches relier/expliquer prêtes) et
`agents-sources` prêts. Run manuel Actions + `GEMINI_API_KEY`, `force_dry_run` décoché. **Je n'ai pas de
clé et n'ai lancé aucun run API** — rien n'est présenté comme exécuté. Les métriques demandées
(fournisseur/modèle/tokens/rejets/gain L3-L4) seront dans le résumé du run réel.

## Phase 15 — Routine
Cycle déterministe (curator → inspector-evaluator → coverage/quality). LLM gaté (knowledge-builder, sources).
Exposition `/ia/inspecteur/` reconstruite par `build_inspector_ia.py` (après `build_ia.py`), jamais par les
agents (périmètre agent-work strict).

## Statut honnête (Phase 16)
- **Réel/vérifié** : statuts de validation, pont contrôlé, projection enrichie, cas-clients, **lien public
  en ligne**, campagnes mono/multi/cas sur artefacts exposés, 244 tests.
- **Simulé (étiqueté)** : L3-internes/L4 (jamais exposés comme vérité ; bloc dédié si présents).
- **Préparé, non exécuté** : campagnes API (pas de clé).
- **En attente humaine** : runs API (secrets), revue des propositions, merge PR, pont graphe-enrichi→
  exposition une fois L3/L4 validés.

## Sécurité
Masters intacts ; pages /ia existantes intactes (seul pointeur additif du manifeste) ; aucun secret ;
aucun usage payant ; aucune interprétation présentée comme clause ; règles externes datées/séparées ;
non-validé jamais présenté comme validé.
