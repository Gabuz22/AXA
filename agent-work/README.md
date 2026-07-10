# Atelier d'agents Gabriel AXA

Un atelier autonome de **mini-agents gratuits** qui préparent en continu de petites améliorations du
projet Gabriel AXA. Pendant que vous ne travaillez pas dessus, ils transforment lentement des zones
d'incertitude en **propositions sourcées, structurées et directement révisables**. Quand vous revenez,
Claude reprend le travail en lisant **un seul fichier** (`coordinator/READY_FOR_REVIEW.md`).

> **Principe de sécurité** : les agents ne modifient **jamais** les masters, l'application, la Vue IA
> publiée, ni `main`. Ils écrivent **uniquement** dans `agent-work/`, sur une branche dédiée, via une
> pull request **jamais fusionnée automatiquement**. Au moindre doute : **fail-closed** (rien n'est écrit).

## Objectif

Transformer, sans intervention humaine et à faible coût, de petites zones d'incertitude en propositions
prêtes à examiner : extractions potentielles, changements de sources officielles, tests de routage,
relations conceptuelles, incidents qualité, améliorations UX — **toujours sourcées, jamais appliquées seules**.

## Architecture

```
agent-work/
  config/        agents.json · providers.json · policies.json · schedules.json
  backlog/       backlog.json (micro-tâches) · completed.json · blocked.json
  <agent>/pending|reviewed|rejected   propositions par agent
  quality/reports · quality/incidents
  official-sources/pending|changes|snapshots|reviewed|rejected
  coordinator/   READY_FOR_REVIEW.md/.json · conflicts.json · statistics.json
  runs/manifests · runs/logs           traçabilité de chaque run
  schemas/       proposal · run-manifest · backlog (JSON Schema)
  scripts/       orchestrator · provider_router · validate_scope · validate_proposal
                 deduplicate · build_review_summary · select_task · quota_manager · safety_checks
                 agents/ (un module par agent) · providers/ (adaptateurs) · tests/
```

Flux d'un run : **préflight sécurité → sélection d'une micro-tâche → exécution de l'agent →
validation (schéma + règles) → déduplication → écriture dans `agent-work/<agent>/pending` →
manifeste**. Le commit, le contrôle de périmètre et la PR sont gérés par le workflow, et **sautés en dry-run**.

## Agents

**Fonctionnent sans aucune API (déterministes, gratuits, planifiés) :**

| Agent | API ? | Sorties | Planning |
|---|---|---|---|
| `quality` | non | `quality/reports`, `quality/incidents` | quotidien 02:17 |
| `coverage-gaps` | non | `quality/incidents` | lun/jeu 04:29 |
| `adversarial-tests` | non (métriques) | `tests/`, incident si régression | mar/ven 04:41 |
| `official-sources` | non (réseau public) | `official-sources/{changes,snapshots}` | lundi 05:13 |
| `coordinator` | non | `coordinator/READY_FOR_REVIEW.*` | quotidien 08:09 |

**Nécessitent une API (LLM) — désactivés, lancement manuel uniquement :**

| Agent | Rôle | État |
|---|---|---|
| `extraction-cg` | extraction sémantique de notices | ⛔ manuel (API requise) |
| `concepts` | relations sémantiques | ⛔ manuel (API requise) |
| `ux-ai` | UX (structure, déterministe) | ⛔ manuel |
| `adversarial-tests` (génération) | nouveaux tests par LLM | ⛔ (le volet métriques reste actif sans API) |

- **Qualité** (sans API) : JSON valides, ai-manifest, sitemap, cohérence de version, synchronisation `/ia`,
  liens internes, pages IA, notices/PDF, IDs stables & doublons, cohérence contrats↔pages↔matrices, couverture,
  tests de routage, orphelins, pages sans source. **Régénère `/ia` pour lire les métriques puis restaure l'arbre.**
  Compare au rapport précédent : anomalie **nouvelle / connue / corrigée**. Incidents à **identifiant stable**
  (pas d'accumulation ; un problème corrigé disparaît).
- **Coverage-gaps** (sans API) : sur **données structurées uniquement** — catégories absentes, contrats sans
  notice, concepts non reliés, écarts de couverture. Ne dit jamais « manque dans le contrat », seulement
  « absente des données structurées » / « vérification documentaire humaine nécessaire ».
- **Tests** (sans API) : relance le harness de routage, mesure précision/rappel/périmètre/source/statut/faux
  positifs, **compare au run précédent** et lève un incident si une métrique **baisse**. N'invente pas de test
  sans modèle (génération LLM = manuelle).
- **Sources officielles** (sans API, réseau) : statut HTTP, redirection, empreinte ; classe
  `indisponible | redirection | contenu_modifie | contenu_inchange | verification_humaine_requise`. **N'interprète jamais.**
- **Coordinateur** (sans API) : agrège, valide, déduplique, score, distingue **réel vs fixture** et
  **nouvelle / connue / corrigée / régression**, produit la synthèse compacte pour Claude.
- **Extraction / Concepts** (API requise) : désactivés tant qu'aucune clé n'est configurée.

## Agent Extraction documentaire (premier agent IA)

`extraction-llm` est un **agent de production**, pas un assistant : il ne répond à personne et ne modifie
jamais le produit. Il prépare des propositions d'ajout **vérifiables**, écrites uniquement dans
`agent-work/extraction/pending/`.

- **Fiabilité avant volume.** Chaque item passe une **porte déterministe anti-hallucination** : la
  `citation` doit réellement figurer sur la **page citée** de la notice (vérifié par lecture du PDF),
  sinon l'item est **rejeté**. Rejets aussi si : hors catégorie, mauvaise page, texte/citation absents,
  doublon, confiance trop faible. Mieux vaut 2 excellentes propositions/semaine que 50 médiocres.
- **Micro-zones.** 2 à 5 pages par zone, **≤ 2 zones par exécution**. Une **mémoire**
  (`agent-work/extraction/memory.json`) retient pages traitées / refusées / zone suivante par contrat —
  aucune relecture inutile ; progression lente et réelle sur des mois.
- **Tokens minimaux.** Le LLM ne reçoit que : les pages de la zone (tronquées), les libellés déjà
  présents, les concepts et catégories, et rien d'autre. Il répond en **JSON strict** (aucune rédaction
  libre). Estimation ~1,5–3 k tokens d'entrée + ~0,5–1 k de sortie **par zone** → **coût nul** (paliers
  gratuits GitHub Models > Gemini > Groq). Budget par run borné ; **arrêt propre** si aucun fournisseur
  gratuit ou quota épuisé.
- **Pipeline de contrôle.** Les propositions passent ensuite les agents **déterministes** (Quality =
  JSON/format/source/page/doublon ; Coverage = comble-t-elle un vrai trou ?) puis le **Coordinateur** les
  classe (nouvelle / doublon / incertaine / rejetée / prioritaire). Les déterministes peuvent invalider l'IA.
- **Dépendance** : `pypdf` (gratuit), installé par le workflow. Sans clé LLM **ou** sans `pypdf`,
  l'agent s'arrête proprement (`no_work`).
- **Activation** : `.github/workflows/agents-extraction-llm.yml` (manuel ; décommenter `schedule` +
  configurer un secret fournisseur + `AGENTS_ENABLED=true` pour l'autonomie).

## Fournisseurs gratuits

Couche multi-fournisseurs configurable dans `config/providers.json` (aucun quota/modèle/URL codé en dur).
Adaptateurs : **GitHub Models, Gemini, Groq, Cloudflare Workers AI, OpenRouter (modèles `:free` uniquement)**.
Le routeur choisit un fournisseur gratuit disponible, respecte un budget par run, gère les 429 (cooldown +
bascule), et **s'arrête proprement** si aucun quota gratuit n'est disponible.

`policies.json` impose `"allow_paid_usage": false`. Le **préflight refuse de démarrer** si un fournisseur
activé n'est pas `free_tier` / est `requires_paid`. ⚠️ On ne peut pas **garantir** qu'une API restera
gratuite : la gratuité est traitée comme une capacité configurable, revérifiée à l'exécution via les erreurs de quota.

## Secrets (à ajouter par vous)

Dans **Settings → Secrets and variables → Actions → Secrets** du dépôt (aucun n'est obligatoire ; sans
secret, les agents LLM s'arrêtent proprement) :

```
GITHUB_MODELS_TOKEN     GEMINI_API_KEY     GROQ_API_KEY
CLOUDFLARE_ACCOUNT_ID   CLOUDFLARE_API_TOKEN   OPENROUTER_API_KEY
```

Et dans **Variables** :

- `AGENTS_ENABLED` = `true` pour autoriser les runs **planifiés** (sinon les schedules ne font rien).
- `AGENTS_DRY_RUN` = `true` pour forcer le dry-run partout (sécurité lors de la première activation).

Les secrets ne sont **jamais** affichés dans les logs (masquage systématique).

## Planification

Horaires **espacés** (jamais tous ensemble) — voir `config/schedules.json` et les `cron` des workflows :
qualité quotidien · extraction 3×/sem · tests 2×/sem · coordinateur quotidien (après les autres).
Sources / concepts / UX sont **désactivés par défaut** (bloc `schedule` commenté). Tous ont `workflow_dispatch`
(lancement manuel), par défaut en **dry-run**.

## Sécurité (compensation de la contrainte GitHub)

GitHub ne peut pas limiter un jeton d'écriture à un dossier. Compensation stricte :

1. travail sur `agents/proposals`, **jamais** sur `main` ;
2. `validate_scope.py` refuse tout fichier hors `agent-work/` **avant** commit (fail-closed) ;
3. un fichier interdit ⇒ le run échoue, **aucun commit** ;
4. **aucune fusion automatique** dans `main` (PR persistante, revue humaine) ;
5. `main` protégé (voir `CODEOWNERS` + réglages de branche) ;
6. aucune exécution de code/commande fourni par un LLM ; sorties filtrées et bornées ;
7. contenu externe (PDF, web) = **donnée**, jamais instruction (règle anti-injection permanente).

## Limites

- 1 agent, 1 micro-tâche, ≤ 5 propositions, budget de tokens borné par run ; pas de boucle autonome.
- Les agents **proposent**, ils ne décident pas de la vérité et n'appliquent rien.
- Les métriques de « travail économisé » sont indicatives (`coordinator/statistics.json`).

## Comment…

**…désactiver tous les agents** : mettre la variable `AGENTS_ENABLED` sur autre chose que `true`
(ou la supprimer). Les schedules ne feront plus rien. Pour couper aussi le manuel, désactiver les
workflows dans l'onglet **Actions**.

**…lancer un agent manuellement** : onglet **Actions → agents-\<nom\> → Run workflow** (laisser
`force_dry_run` coché pour un essai). En local :
```
python agent-work/scripts/orchestrator.py --agent quality --dry-run
python agent-work/scripts/orchestrator.py --agent quality --mock   # exemple sans LLM ni réseau
python agent-work/scripts/build_review_summary.py                  # régénère la synthèse
```

**…examiner les propositions** : lire `coordinator/READY_FOR_REVIEW.md`, puis ouvrir uniquement les
fichiers listés en haute priorité (`<agent>/pending/*.json`). Chaque proposition porte sa source, sa
confiance, ses risques et `validation_required`.

**…accepter / rejeter / archiver** :
- **accepter** : appliquer manuellement le changement dans le produit (hors `agent-work/`), puis déplacer
  le fichier de `pending/` vers `reviewed/`.
- **rejeter** : déplacer le fichier vers `rejected/` (garde une trace).
- **archiver** : conserver dans `reviewed/` ; le backlog et les stats gardent l'historique.

**…éviter de lire trop de fichiers** : ne lire que `READY_FOR_REVIEW.md` puis les 5 propositions
prioritaires. Ne jamais parcourir `runs/logs/` sauf incident précis.

## Reprise du projet avec Claude

Protocole (économie de tokens — Claude ne refait pas le travail préparatoire) :

1. lire **`agent-work/coordinator/READY_FOR_REVIEW.md`** (et lui seul pour commencer) ;
2. lire **uniquement** les propositions prioritaires qui y sont listées ;
3. **vérifier les sources** de chaque proposition retenue (notice + page ; la notice PDF fait foi) ;
4. corriger si nécessaire ;
5. **appliquer manuellement** les changements validés dans le produit (jamais via les agents) ;
6. déplacer les propositions traitées dans `reviewed/` ou `rejected/` ;
7. **ne jamais** demander à Claude de relire tous les logs.

## Tests

```
python -m unittest discover -s agent-work/scripts/tests -p "test_*.py"
```
Vérifie : périmètre, chemins interdits, JSON invalide, doublons, source obligatoire, réglementaire non
auto-validable, master toujours `validation_required`, secrets absents des logs, arrêt sur quota, synthèse
coordinateur, bornage (pas de boucle infinie), dry-run sans écriture.
