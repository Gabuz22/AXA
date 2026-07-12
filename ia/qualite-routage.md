# Qualité du routage — mesures de précision

> **Vue IA de Gabriel AXA** — projection statique des JSON, lisible sans JavaScript. Générée le 2026-07-12 (v2.1.0).
> Masters non modifiés ; données de sources publiques ; **la notice PDF fait foi.**

**Objectif.** Précision du moteur de détection/routage : contrats, périmètre, sources officielles, statut. Les erreurs restantes sont listées par famille.

**Règles.** Pack A = preuve contractuelle. Pack B = raisonnement (jamais une preuve seule). Toujours citer la source (notice, page). Ne jamais inventer ; si une information est absente, le dire. La notice PDF fait foi.

**Limites.** Certains tableaux chiffrés (valeurs de rachat, barèmes) sont à vérifier dans la notice. La notice PDF reste la seule source qui fait foi.


## Métriques globales (76 tests)
| Mesure | Valeur |
|---|--:|
| Tests passés | 76 / 76 |
| Précision contrats | 100 % |
| Rappel contrats | 100 % |
| Faux positifs (contrats interdits apparus) | 0 |
| Faux négatifs (contrats obligatoires manquants) | 0 |
| Exactitude périmètre mono/multi | 100 % |
| Exactitude déclenchement source officielle | 100 % |
| Exactitude statut de conclusion | 83 % |
| Exactitude catégories | 98 % |

## Par famille
| Famille | Passés |
|---|--:|
| ambigu | 3/3 |
| comparaison | 2/2 |
| contractuel_strict | 9/9 |
| reglementaire | 6/6 |
| sans_reponse | 4/4 |
| transversale | 15/15 |
| validation | 10/10 |
| verrou_contrat | 27/27 |

## Erreurs restantes (0)
_Aucune erreur : tous les parcours sont corrects._