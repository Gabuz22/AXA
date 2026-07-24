# Endpoint de calcul — mise en service Cloudflare Pages

Ce dépôt contient désormais `functions/api/preselection.js` : une Cloudflare Pages Function qui
**exécute réellement** le moteur de présélection (même barème, mêmes correctifs que
`app/services/axaPreselection.js`) au lieu de laisser une IA le ré-approximer en lisant le JSON.

Elle est **complète, testée en local** (émulateur `wrangler pages dev`, 4 scénarios vérifiés :
score correct, donnée nominative refusée, âge hors plage détecté, écriture refusée). Il ne reste
qu'une étape que je ne peux pas faire à ta place : **relier ce dépôt à un compte Cloudflare**, ce
qui demande ta propre authentification (je ne dois jamais voir ni saisir ton mot de passe).

## Ce qui existe déjà (rien à toucher)

- `functions/api/preselection.js` — la Function, en lecture seule, aucune écriture possible.
- Le protocole `start.html` a une ligne **prête mais désactivée** (`CLOUDFLARE_API_BASE = None`
  dans `scripts/build_ia.py`) : tant que le projet n'existe pas, aucun lien mort n'est publié.

## Ce qu'il te reste à faire (≈5 minutes, comme pour gabriel-virtuel.pages.dev)

1. **[dash.cloudflare.com](https://dash.cloudflare.com)** → connecte-toi avec ton compte habituel.
2. Menu **Workers & Pages** → **Créer une application** → onglet **Pages** → **Se connecter à Git**.
3. Autorise l'accès au dépôt **`Gabuz22/AXA`** (GitHub te demandera une confirmation — normal).
4. Réglages de build :
   - Nom du projet : `axa-ia` (ou un autre nom — il déterminera l'URL `<nom>.pages.dev`)
   - Branche de production : `main`
   - Commande de build : **laisser vide** (rien à compiler)
   - Répertoire de sortie : **`/`** (racine du dépôt)
   - `functions/` est détecté automatiquement — rien à configurer pour ça.
5. **Déployer**. Cloudflare te donne une URL du type `https://axa-ia.pages.dev`.
6. **Teste** : `https://axa-ia.pages.dev/api/preselection?age=42&besoins=emprunt:100` doit répondre
   un JSON avec `"classes": [...]` (Masterlife CREDIT doit ressortir en tête).

## Ce que je ferai une fois l'URL connue

Donne-moi l'URL exacte (`https://<nom>.pages.dev`) et je :
1. mets `CLOUDFLARE_API_BASE` à cette valeur dans `scripts/build_ia.py` ;
2. reconstruis la Vue IA (`python scripts/build_ia.py`) — la ligne apparaît alors dans `start.html`,
   `start.txt` et la carte des parcours, exactement comme prévu ;
3. vérifie que le lien répond réellement (pas seulement qu'il est présent) ;
4. commit et pousse.

## Garde-fous déjà en place dans la Function

- **Lecture seule** : `POST` renvoie 405, aucune route d'écriture n'existe.
- **Aucune donnée nominative acceptée** : tout paramètre ressemblant à un nom, un email, un
  téléphone ou une adresse est rejeté explicitement (HTTP 400).
- **Aucune donnée dupliquée** : la Function lit les mêmes JSON que GitHub Pages, dans le même
  déploiement (`env.ASSETS.fetch`) — pas de deuxième source de vérité, pas de risque de dérive.
- **Dégradation propre** : si Cloudflare tombe un jour, la Vue IA continue de fonctionner à
  l'identique sur GitHub Pages — seule la présélection chiffrée devient indisponible.
