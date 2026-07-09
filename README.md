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

## Structure

```
/                     index.html (redirige vers app/)
app/                  l'application
  index.html          entrée
  app.js              shell : navigation conseiller + routeur + aide + thème
  assets/app.css      design system (sobriété pro)
  modules/            axa.js (sections), axa_content.js
  services/           axaKnowledge.js (recherche BM25 sourcée), markdown.js, humanView.js
  state/store.js      préférences (thème)
  vendor/             marked, DOMPurify (rendu Markdown sûr, hors ligne)
data/AXA/             masters Pack A/B, vues humaines, index PDF, contrats, dérivés, notices
```

## Doctrine

- **Pack A** = la preuve contractuelle (fait foi). **Pack B** = le raisonnement (jamais une preuve seule).
- Toute réponse client se vérifie sur la **notice PDF**.

## Statut

Version 0.2 — extraction autonome, design system, accueil-promesse. Prochaines étapes : onboarding
(Bienvenue / FAQ / mode démo), copilote décisionnel, page « Utiliser avec une IA » + Téléchargements.
