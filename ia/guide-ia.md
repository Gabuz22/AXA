# Guide IA — comment utiliser Gabriel AXA

> Page destinée à une IA ou un agent. Explique comment travailler à partir de la Vue IA seule.
> **Commence par les [Instructions maîtres](instructions-maitres.html)** : c'est le protocole à appliquer avant de répondre. Ce guide en détaille la navigation.

## Comment utiliser Gabriel AXA
La Vue IA est la **projection complète et sourcée** de la base contractuelle AXA. Tu peux travailler
**uniquement** depuis ces pages (HTML/Markdown) sans les JSON. Chaque affirmation contractuelle porte
sa source (notice + page).

## Comment répondre
- Réponds **uniquement** à partir des contenus présents, **avec leur source** (notice, page).
- **Pack A = preuve** ; **Pack B = raisonnement** (jamais cité seul comme preuve).
- Sépare clairement ce qui est **contractuel** (Pack A / notice) de ce qui est **raisonnement** (Pack B).
- Termine en renvoyant à la **notice PDF**, qui fait foi.

## Comment rechercher
1. Par contrat : `/ia/contrats.html` → `/ia/contrat/<slug>.html`.
2. Par catégorie : `/ia/garanties.html`, `/ia/exclusions.html`, `/ia/definitions.html`, `/ia/conditions.html`,
   `/ia/declencheurs.html`, `/ia/plafonds.html`, `/ia/franchises.html`.
3. Par thème : `/ia/themes.html` (invalidité, décès, hospitalisation, rachat, souscription, fiscalité, association, ANPERE).
4. Glossaire : `/ia/glossaire.html`. Sources : `/ia/sources.html`. Notices : `/ia/notices.html`.

## Quand citer
**Toujours**, dès qu'une information est contractuelle. Format : `[Notice : <fichier>, p.<page>]` (lien vers le PDF).
Chaque élément possède aussi un **identifiant stable** (`#<id>`) réutilisable pour référencer précisément.

## Comment arbitrer entre plusieurs contrats
Compare via les pages catégorie ou thème (qui agrègent tous les contrats). Ne mélange jamais les garanties
d'un contrat avec un autre : chaque élément indique son contrat. En cas de doute, ouvre les deux fiches contrat.

## Comment gérer une absence d'information
Si l'information n'apparaît pas dans la Vue IA : dis-le explicitement (« non présent dans la base Gabriel AXA »),
propose la notice PDF du contrat, **n'invente pas**.

## Comment utiliser les liens
- Contrat → ses garanties/définitions (mêmes pages, ancres `#id`) → **notice** → **page PDF** exacte (`#page=`).
- Catégorie/Thème → lien vers le contrat concerné → retour thème.
Suis la hiérarchie : **Index → Contrat/Catégorie/Thème → Élément → Notice → Page PDF**.

## Hiérarchie d'autorité
1. **Notice PDF** (fait foi). 2. **Pack A** (donnée contractuelle dérivée, à citer). 3. **Glossaire** (définitions sourcées).
4. **Pack B** (raisonnement ; jamais une preuve seule).

## Exemple de BONNE réponse
« Pour MasterLife, le décès accidentel double le capital (Notice MasterLife, p.6). À confirmer sur la notice. »

## Exemple de MAUVAISE réponse
« Oui, remboursé à 100 %. » — aucune source, non vérifiable, invention possible.
