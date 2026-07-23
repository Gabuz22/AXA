# Graphe de preuves

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-17 (v2.3.0).
> Outil **indépendant et non officiel**, non affilié ni validé par AXA — documents accessibles publiquement.
> Masters non modifiés ; **la notice PDF fait foi** ; vérification humaine avant toute réponse au client.
> IA : n'utilise jamais ta mémoire générale ici — cite [Contrat — Notice, p.X] ou signale l'absence. Première visite : [START](https://gabuz22.github.io/AXA/ia/start.html).

**Objectif.** Chaque élément citable comme preuve, avec id stable, contrat, type, texte, source PDF + page, liens et concepts. Une conclusion doit reposer sur des ids précis.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.

## Principe
Toute conclusion se reconstruit depuis des **preuves identifiées** : « cette conclusion repose sur les éléments `#id1`, `#id2`, `#id3` ».
Chaque preuve porte : contrat · type · texte · **source PDF + page** · lien contrat · lien notice · concepts liés.

## Format machine
- [preuves.json](preuves.json) — 647 éléments. Relations dérivées (même contrat, concepts partagés) ; aucune relation inventée.

## Comment citer une preuve
`[Notice : <fichier>, p.<page>]` + l'`#id` de l'élément (réutilisable, stable).
