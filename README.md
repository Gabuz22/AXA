# Gabriel AXA

**Assistant conseiller AXA** — la base de connaissances contractuelle, sourcée, pour **gagner du temps** :
retrouver une garantie, une exclusion, une définition ou une condition, toujours reliée à la notice qui fait foi.

> Application métier autonome, sans build. Aucune IA branchée, aucune clé API, aucune donnée client.
> Les documents contractuels embarqués proviennent de **sources publiques** (notices d'information / CG diffusées par AXA).
> **La notice PDF fait toujours foi.**

## Lancer en local

Aucune installation : servez la racine du dépôt en statique, puis ouvrez l'application.

```bash
python start_local_server.py
# puis http://127.0.0.1:8787/   (redirige vers /app/)  — ou directement /app/index.html
```

N'importe quel serveur statique fait l'affaire (l'app est en modules ES natifs).

## Ce que ça fait

- **Recherche** en langage naturel (garanties, exclusions, définitions, conditions), sourcée.
- **Fiches contrat** (par ordre alphabétique) avec renvoi à la notice à la bonne page.
- **Copilote de réponse** : preuves contractuelles (Pack A) + raisonnement (Pack B), séparés, avec brief copiable.
- **Comparateur**, **glossaire**, **notices PDF**, **outils conseiller** (analyse des besoins, préparation RDV, animateur).
- **Utiliser avec une IA** : mode d'emploi Pack A / Pack B pour ChatGPT ou Claude.

## Vue IA (`/ia`) — couche pour les modèles

Un espace **statique** destiné aux IA et agents : pages `.html` **et** `.md` lisibles **sans JavaScript**,
à URLs directes stables, entièrement sourcées. Une IA peut recevoir la seule URL `…/ia/` et comprendre
comment exploiter Gabriel AXA sans qu'on lui fournisse les JSON.

- Point d'entrée : [`/ia/`](ia/index.html) · Mode d'emploi IA : [`/ia/mode-emploi-ia.html`](ia/mode-emploi-ia.html)
- Pack A : `/ia/pack-a.html` · `/ia/pack-a.md` — Pack B : `/ia/pack-b.html` · `/ia/pack-b.md`
- Glossaire, Contrats, Index transverse, une page par contrat (`/ia/contrats/<slug>.html|.md`)
- Machine : `/ia/ai-manifest.json`, `/ia/sitemap-ia.xml`, `/ia/robots.txt`, `/ia/contrats.json`, `/ia/glossaire.json`

Régénérer après mise à jour des données : `python scripts/build_ia.py` (dérivé, ne touche pas aux masters).

## Structure

```
/                     index.html (redirige vers app/)
app/                  l'application (SPA conseiller)
  index.html · app.js · assets/app.css · modules/ · services/ · state/ · vendor/
ia/                   COUCHE IA STATIQUE générée (html + md + json + manifest + sitemap)
data/AXA/             masters Pack A/B, vues humaines, index PDF, contrats, dérivés, notices
scripts/build_ia.py   générateur de la couche IA
```

## Doctrine

- **Pack A** = la preuve contractuelle (fait foi). **Pack B** = le raisonnement (jamais une preuve seule).
- Toute réponse client se vérifie sur la **notice PDF**.

## Statut

Version 0.2 — extraction autonome, design system, accueil-promesse. Prochaines étapes : onboarding
(Bienvenue / FAQ / mode démo), copilote décisionnel, page « Utiliser avec une IA » + Téléchargements.
