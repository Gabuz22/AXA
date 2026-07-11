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
