# Architecture — De l'extraction documentaire à la plateforme de construction de connaissances

> Statut : **fondation posée (v2.8, phase 0)**, feuille de route validée par étapes additives.
> Portée : `agent-work/` uniquement. Ne modifie jamais le produit, les masters, ni les workflows existants.

## 1. Le changement de nature

Hier : *extraire des faits absents des notices*. Demain : *construire progressivement une représentation
fidèle, profonde et continuellement enrichie d'un domaine documentaire*. AXA est le **premier domaine**,
pas le sujet. L'architecture doit tenir avec 1 000 contrats, des milliers de PDF et plusieurs domaines,
**sans devenir un patchwork**.

## 2. Principe directeur (l'invariant des 5 prochaines années)

> **La connaissance est la plateforme. Les agents sont des fonctions sur elle. Le travail est une donnée.**

Trois conséquences qui gouvernent tout le reste :

1. **Un graphe de connaissances unique** est la source de vérité. Les mémoires éparses actuelles
   (`coverage_map`, mémoire d'extraction, `learning.json`, `tasks.json`) deviennent des **projections** ou
   des **producteurs** de ce graphe, pas des vérités concurrentes.
2. **Les agents sont uniformes et sans état** : ils lisent le graphe, produisent des nœuds/arêtes/tâches,
   et s'arrêtent. Aucun agent ne « possède » sa vérité.
3. **Le travail (les tâches) est une donnée typée** dérivée de l'état du graphe. Le système *découvre* le
   travail au lieu de le coder en dur.

## 3. Là où je remets en cause la mission (et pourquoi)

La mission liste ~15 agents (Knowledge Builder, Relation Builder, Duplicate Finder, Contradiction Finder,
Freshness Checker, Task Generator, Cost Optimizer…). **Construire 15 agents serait exactement le patchwork
que l'on veut éviter.** La plupart de ces « agents » sont en réalité des **passes déterministes sur le
graphe** — donc **zéro token**. Je propose de les répartir ainsi :

| Idée de la mission | Ce que c'est réellement | Coût |
|---|---|---|
| Duplicate Finder, Contradiction Finder, Freshness Checker, Coverage Builder, Task Generator, Cost Optimizer, Reasoning Optimizer | **Passes DÉTERMINISTES** sur le graphe (dédup par hash, TTL, vecteurs de couverture, génération de tâches) | 0 token |
| Corpus Explorer | **Déjà construit** (v2.7) — devient un *producteur de L1* | quasi 0 |
| Knowledge Builder, Relation Builder, Concept Builder, Environment/Official Sources Builder, Knowledge Reviewer | **Capacités LLM** (peu nombreuses, génériques) appelées **seulement** sur les axes faibles | LLM ciblé |
| Learning Manager | Politique + `learning.json` déjà existant | 0 |

→ **~4 capacités LLM + un petit noyau de passes déterministes**, pas 15 agents. Chaque nouvelle
« capacité » est un module uniforme, pas une architecture. C'est ce qui reste maintenable à 40 agents.

Second choix assumé : **la couverture n'est plus un nombre de pages** mais un **vecteur de profondeur**
calculé sur le graphe (voir §5). C'est ce qui fait passer d'« extraire » à « comprendre ».

## 4. Le graphe de connaissances en 4 couches — `knowledge_graph.py`

Chaque connaissance appartient à des couches (le **sens**, pas le PDF) :

```
L1  evidence       (document, page, citation, hash)      immuable, append-only, sourcée
L2  normalized     entité canonique (garantie, exclusion, concept…), dédupliquée, typée
L3  relation       arête typée : depends_on, excludes, complements, triggers, requires,
                   limits, replaces, comparable_to, governed_by, explains, refines, contradicts
L4  understanding  synthèse/explication rattachée à une entité, recalculable, tracée vers L1/L3
```

Invariants (garants de robustesse) :

- **Domaines séparés, relations transverses.** Une clause contractuelle (`domain="axa-contrat"`) et une
  règle fiscale (`domain="fiscalite"`) ne se mélangent JAMAIS dans le même nœud ; mais une arête
  `governed_by` peut les relier. → satisfait « ne jamais mélanger clauses et environnement » tout en
  permettant le raisonnement inter-domaines.
- **Provenance + fraîcheur + confiance sur CHAQUE nœud/arête** : `sources[]`, `freshness{as_of, ttl_days,
  checked_at}`, `confidence`. La connaissance réglementaire porte sa source officielle, sa date, sa
  péremption.
- **Évidence immuable** : une correction crée un nouveau nœud et `supersede` l'ancien (jamais d'écrasement
  d'une preuve).
- **Déduplication déterministe par identité canonique** (`evidence_id`, `entity_id`, `relation_id`) →
  reruns idempotents, zéro doublon. Une entité garde son identité même quand son contenu s'enrichit
  (`revision++`).

## 5. Couverture = PROFONDEUR — `coverage_model.py`

Vecteur par sujet, **calculé déterministiquement** sur le graphe (aucun token) :

```
evidence · normalized · relations · understanding · environment · freshness   → depth_score ∈ [0..1]
```

Une entité **extraite mais isolée** (pas de relation, pas d'explication) est « connue mais superficielle ».
`generate_deepening_tasks` produit alors des tâches **relier / expliquer / comparer / environnement**,
**même sans nouvelle phrase à extraire**. C'est l'implémentation directe de « approfondir, pas seulement
compléter ». Le seuil pilote l'effort ; les axes les plus faibles sont traités en premier.

## 6. Le modèle d'agents — noyau + bus de travail

```
              ┌─────────────────── graphe de connaissances (source de vérité) ───────────────────┐
              │  L1 evidence · L2 entities · L3 relations · L4 understanding · provenance/fraîcheur │
              └───────▲───────────────────────────────────────────────────────────▲──────────────┘
   producteurs        │ écrivent                                        lisent      │
   (agents/capacités) │                                                             │  passes DÉTERMINISTES
   ┌──────────────────┴───────────────┐                        ┌────────────────────┴──────────────────┐
   │ corpus-explorer  (L1, déjà là)   │                        │ coverage-model  (vecteurs de profondeur)│
   │ knowledge-builder (L2, LLM)      │                        │ gap/task-generator (tâches typées)      │
   │ relation-builder  (L3, LLM)      │                        │ duplicate / contradiction / freshness   │
   │ understanding-builder (L4, LLM)  │                        │ cost-ledger (gouvernance)               │
   │ environment-builder (L2/L3 env)  │                        └────────────────────┬──────────────────┘
   └──────────────────▲───────────────┘                                             │ émettent des TÂCHES
                      │                                                              ▼
                      └──────────────  task_queue (orchestrateur existant)  ◀────────┘
                                        routage multi-fournisseurs · budget · AGENT_RESULT_JSON
```

- **Les agents produisent aussi du travail** : une capacité, en s'exécutant, émet de nouvelles tâches
  (une explication crée un besoin de comparaison ; une contradiction crée une vérification). Le travail
  circule comme une donnée dans la file existante.
- **L'orchestrateur est réutilisé tel quel** : routage, budget, `blocked_human_review`, workflows. On ne
  réimplémente rien.

## 7. Gouvernance des coûts — déterministe d'abord

Objectif majeur : **minimiser les tokens**. Règles :

1. **Tout ce qui peut être déterministe l'est** : cartographie, zonage, couverture, dédup, contradiction
   lexicale, fraîcheur, génération de tâches → **0 token**.
2. **Un appel LLM doit être justifié** par un axe de profondeur sous le seuil **ET** un contenu
   nouveau/changé (hash/diff). Le graphe est le portier.
3. **Cost-ledger** (phase 2) : budget par domaine/semaine, valeur estimée par tâche, l'orchestrateur
   ordonne par valeur/coût. « Je ne relis que ce qui est nouveau ou insuffisamment compris. »

## 8. Généricité — Domaine = adaptateur

Un `DomainAdapter` (interface, phase 1) expose : `documents()`, `known_terms()`, `label_rules()`,
`namespaces()`, `official_sources()`. **AXA devient un simple adaptateur.** Le graphe, la couverture, la
génération de tâches, l'orchestrateur sont domain-agnostiques. Demain : `bofip`, `has`, `openai-docs`,
`journal-gabriel` = de nouveaux adaptateurs, **sans toucher au moteur**.

```
AXA → adaptateur ┐
BOFiP → adaptateur ┤→ même moteur (graphe + couverture + tâches + orchestrateur) → connaissance par domaine
HAS → adaptateur ┘
```

## 9. Feuille de route (additive, rétrocompatible, résiliente)

| Phase | Contenu | État |
|---|---|---|
| **0 — Fondation** | `knowledge_graph.py` (4 couches, provenance/fraîcheur/dédup) + `coverage_model.py` (profondeur) + schéma + tests | **✅ livré (v2.8)** |
| **1 — Adaptateur & alimentation** | `domain_adapter.py` (interface + registre) + `domains/axa.py` + `knowledge_ingest.py` (ingestion DÉTERMINISTE : connaissance structurée → L2+L1, propositions extraction → L1+L2 ; idempotent, 0 token). Vérifié : 196 entités L2 + 140 preuves L1 sur 9 contrats | **✅ livré (v2.8)** |
| **2 — Passes déterministes** | `knowledge_ops.py` (dup/contradiction/freshness + CostLedger) + `knowledge_tasks.py` (backlog vivant pending↔resolved) + agent `knowledge-curator` branché au cycle (ingest + profondeur + backlog, **0 token**) | **✅ livré (v2.8)** |
| **3 — Capacités LLM ciblées** | `knowledge_build.py` (relations L3, compréhension L4, LLM injecté) + agent `knowledge-builder` (budget + cost-ledger, fail-open) + workflow dédié. N'appelle le LLM que sur les axes faibles | **✅ livré (v2.8)** |
| **4 — Environnement** | environment-builder : fiscalité/réglementation en domaines séparés, reliés par `governed_by` (part déterministe depuis `sources-officielles.json`, part réseau via l'agent official-sources existant) | à valider (réseau) |
| **5 — Projection produit** | export lecture seule du graphe vers une future Vue IA enrichie (jamais d'écriture produit auto) | à valider (proximité produit) |

Chaque phase est **additive** (nouveaux fichiers), **rétrocompatible** (l'existant continue de tourner),
**résiliente** (état persistant sauvé incrémentalement, restauré depuis `agents/proposals`), **générique**
(rien de spécifique à AXA dans le moteur).

## 10. Déjà livré dans cette pierre

- `scripts/knowledge_graph.py` — graphe générique 4 couches, provenance/fraîcheur/confiance, dédup
  déterministe, évidence immuable, supersession, requêtes.
- `scripts/coverage_model.py` — vecteur de profondeur + `generate_deepening_tasks` déterministe.
- `schemas/knowledge_node.schema.json` — contrat durable des nœuds/arêtes.
- `scripts/tests/test_knowledge_platform.py` — 12 tests (couches, domaines séparés + relations transverses,
  dédup/idempotence, évidence append-only, profondeur, tâches d'approfondissement sur entité connue).

**Phase 1 (livrée) :** `scripts/domain_adapter.py`, `scripts/domains/axa.py`, `scripts/knowledge_ingest.py`,
`scripts/tests/test_domain_ingest.py`. L'ingestion déterministe peuple le graphe depuis la connaissance
structurée (avec provenance) et les propositions d'extraction — **0 token**, idempotent, additif.

Aucun agent/workflow/produit existant n'est modifié. Le graphe est alimenté par une passe déterministe
en lecture seule des sorties existantes : **rien ne peut casser**. La prochaine étape (phase 2) branche le
`gap/task-generator` sur le cycle pour que la profondeur manquante devienne des tâches exécutables.
