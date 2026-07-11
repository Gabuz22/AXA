# Configuration des fournisseurs LLM gratuits

Gabriel AXA n'utilise **que des API à quota gratuit**, **sans carte bancaire**, et **jamais** OpenAI ni
GitHub Models (retiré définitivement). Tout est **déclaratif** dans
[`agent-work/config/providers.json`](config/providers.json) : le routeur ne lit que ce fichier.
Pour ajouter/retirer un fournisseur, éditez ce JSON — **aucun code à modifier**.

> ⚠️ Les identifiants de modèles et les quotas gratuits **évoluent**. Ce document donne l'état connu ;
> en cas de changement, mettez à jour `providers.json` (champ `models`) — c'est le seul endroit à toucher.

## Comment ajouter un fournisseur en < 2 min
1. Créer la clé chez le fournisseur (liens ci-dessous) — **aucune carte bancaire**.
2. GitHub → **Settings → Secrets and variables → Actions → New repository secret** → coller la clé sous le **nom exact** indiqué.
3. Dans `providers.json`, mettre le fournisseur `"active": true` (et ajuster `priority`/`models` si besoin).
4. (Optionnel) lancer un run manuel `agents-extraction-llm` : le routeur détecte la clé et l'ajoute à la chaîne de secours.

## Ordre de configuration recommandé (Gemini déjà en place)
`GEMINI_API_KEY` existe déjà. Ajouter ensuite, dans cet ordre, ces secrets GitHub :

**1. `GROQ_API_KEY`** — secours rapide.
- Lien : https://console.groq.com/keys · Étapes : se connecter → *Create API Key* → copier.
- Permissions minimales : lecture d'inférence (clé standard). · Secret GitHub : **`GROQ_API_KEY`**.
- Vérifier : `python agent-work/scripts/provider_router.py` (doit montrer `groq … clé=True éligible=True`).
- Révoquer : console Groq → supprimer la clé. · Risque facturation : **aucun** (palier gratuit, sans carte).
- Garantie zéro-coût côté code : `requires_paid:false`, `allow_paid_usage:false`, budget par cycle borné, arrêt avant dépassement.

**2. `OPENROUTER_API_KEY`** — réserve flexible (`:free` uniquement).
- Lien : https://openrouter.ai/keys · Étapes : se connecter → *Create Key* → copier.
- Permissions minimales : clé standard. · Secret GitHub : **`OPENROUTER_API_KEY`**.
- Vérifier : le routeur montre `openrouter … éligible=True` ; seuls les modèles `…:free` sont appelés (garde `:free` dans le code).
- Révoquer : dashboard OpenRouter → supprimer la clé. · Risque facturation : **aucun tant qu'on reste sur `:free`** —
  le code **refuse tout modèle sans `:free`** (routeur + orchestrateur), budget = 0.

**3. `CLOUDFLARE_API_TOKEN`** — secours indépendant de Google.
- Lien : https://dash.cloudflare.com/profile/api-tokens · Étapes : *Create Token* → gabarit **Workers AI** (lecture) → créer → copier.
- Permissions minimales : **Workers AI : Read/Run** uniquement. · Secret GitHub : **`CLOUDFLARE_API_TOKEN`**.
- Vérifier : routeur `cloudflare … éligible=True` (nécessite aussi l'Account ID ci-dessous).
- Révoquer : page API Tokens → *Delete*. · Risque facturation : **aucun** (allocation quotidienne gratuite).
- Garantie zéro-coût : `requires_card:false`, budget borné, arrêt avant dépassement.

**4. `CLOUDFLARE_ACCOUNT_ID`** — complément obligatoire de Cloudflare.
- Où : dashboard Cloudflare → la page d'accueil/URL contient l'Account ID (32 hex). · Secret GitHub : **`CLOUDFLARE_ACCOUNT_ID`**.
- Vérifier : sans lui, Cloudflare reste `éligible=False`. · Révoquer : non applicable (identifiant, pas un secret sensible).
- Risque facturation : aucun (identifiant seul).

## Ordre recommandé (priorité)
1. **Gemini** — 2. **Groq** — 3. **Cloudflare Workers AI** — 4. **OpenRouter** (`:free` uniquement).
Le routeur affine cet ordre automatiquement selon la **qualité mesurée** (benchmark) et la **fiabilité** observée.

## Secrets GitHub à créer
| Fournisseur | Secret(s) GitHub | Carte bancaire ? |
|---|---|---|
| Gemini | `GEMINI_API_KEY` | Non |
| Groq | `GROQ_API_KEY` | Non |
| Cloudflare | `CLOUDFLARE_API_TOKEN` **+** `CLOUDFLARE_ACCOUNT_ID` | Non |
| OpenRouter | `OPENROUTER_API_KEY` | Non (modèles `:free`) |

Aucun secret n'est obligatoire : sans clé, les agents LLM s'arrêtent proprement (`no_work`). Il suffit
d'**une** clé (Gemini recommandé) pour démarrer.

---

## 1. Gemini (Google AI Studio) — **principal**
- **Intérêt** : gratuit, bonne qualité, JSON fiable ; plusieurs modèles.
- **Modèle recommandé** : `gemini-2.5-flash-lite` (puis `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-1.5-flash`).
- **Quota gratuit** (indicatif) : ~15 req/min et ~1000–1500 req/jour selon le modèle (flash-lite le plus généreux).
- **Limitations** : limites par minute ; certains modèles « pro » ne sont pas gratuits (ne pas les mettre dans `models`).
- **Type de clé** : clé API AI Studio (pas de carte).
- **Où créer** : https://aistudio.google.com/apikey
- **Secret GitHub** : `GEMINI_API_KEY`
- **Exemple** : `GEMINI_API_KEY = AIza...`

## 2. Groq — secours rapide
- **Intérêt** : très rapide, gratuit, JSON ok.
- **Modèle recommandé** : `llama-3.3-70b-versatile` (ou `llama-3.1-8b-instant`).
- **Quota gratuit** (indicatif) : limites par minute (requêtes + tokens) et par jour.
- **Limitations** : débit limité aux heures de forte charge.
- **Type de clé** : clé API console Groq (pas de carte).
- **Où créer** : https://console.groq.com/keys
- **Secret GitHub** : `GROQ_API_KEY`
- **Exemple** : `GROQ_API_KEY = gsk_...`

## 3. Cloudflare Workers AI — secours indépendant de Google
- **Intérêt** : infrastructure différente (résilience), allocation quotidienne gratuite.
- **Modèle recommandé** : `@cf/meta/llama-3.1-8b-instruct`.
- **Quota gratuit** (indicatif) : allocation quotidienne en « Neurons », réinitialisée chaque jour.
- **Limitations** : nécessite l'**Account ID** en plus du token ; qualité un peu en dessous des 70B.
- **Type de clé** : API Token (scope Workers AI) + Account ID (pas de carte).
- **Où créer** : https://dash.cloudflare.com/profile/api-tokens (token) — Account ID visible dans le dashboard.
- **Secrets GitHub** : `CLOUDFLARE_API_TOKEN` **et** `CLOUDFLARE_ACCOUNT_ID`
- **Exemple** : `CLOUDFLARE_API_TOKEN = v1.0-...` · `CLOUDFLARE_ACCOUNT_ID = 0123abcd...`

## 4. OpenRouter — secours ultime (`:free` uniquement)
- **Intérêt** : agrège de nombreux modèles ; certains sont **réellement gratuits** (suffixe `:free`).
- **Modèle recommandé** : `meta-llama/llama-3.3-70b-instruct:free` (ou `google/gemma-2-9b-it:free`).
- **Quota gratuit** (indicatif) : quota partagé limité sur les modèles `:free`.
- **Limitations** : **désactivé par défaut** (`active:false`) ; n'activer qu'avec des modèles `:free` explicites.
  Ne JAMAIS lister un modèle sans `:free` (risque payant).
- **Type de clé** : clé API OpenRouter (pas de carte pour les `:free`).
- **Où créer** : https://openrouter.ai/keys
- **Secret GitHub** : `OPENROUTER_API_KEY`
- **Exemple** : `OPENROUTER_API_KEY = sk-or-...`

---

## Fournisseurs EXCLUS (à ne jamais configurer)
- **OpenAI**, **Anthropic direct**, **Azure OpenAI** : payants / carte requise.
- **GitHub Models** : retiré définitivement (service susceptible de disparaître).
- Tout fournisseur exigeant une **carte bancaire** ou sans **quota gratuit** garanti.

Le préflight (`safety_checks.preflight`) **refuse de démarrer** si un fournisseur actif est marqué
`requires_paid` ou `requires_card`, ou n'est pas `free_tier`. `allow_paid_usage` reste `false`.

## Vérifier la configuration
```
python agent-work/scripts/provider_router.py     # auto-détection + chaîne de secours + métriques
python agent-work/scripts/benchmark_providers.py  # compare la qualité des fournisseurs (mesure seule)
```
