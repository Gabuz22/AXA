# Audit UX exhaustif des routes — Gabriel AXA

Date : 2026-07-12 · Mission produit chantiers 3-10 · Chaque route a été **ouverte réellement au navigateur** (desktop + mobile 375 px), parcourue comme un utilisateur, puis corrigée si nécessaire.

Colonnes : **Intention** (ce que l'utilisateur vient faire) · **Action principale** · **Friction observée** · **Gravité** (haute/moyenne/basse/aucune) · **Décision** · **Correction** (commit) · **Test**.

| Route | Intention | Action principale | Friction observée | Gravité | Décision | Correction | Test |
|---|---|---|---|---|---|---|---|
| `#/accueil` | savoir quoi faire, reprendre | chercher / choisir une intention | accès rapides orientés outils, pas d'intentions ; rien pour reprendre | moyenne | refonte par intention | `aab016c` : « Que veux-tu faire ? » (8 entrées), bloc Reprendre (contexte + 3 dernières recherches + historique), ligne fraîcheur | navigateur : reprise de la comparaison en cours OK |
| `#/recherche` | retrouver une clause sourcée | taper, filtrer, ouvrir la fiche | état vide muet (« aucun résultat ») = cul-de-sac | moyenne | état humain | `aab016c` : explication (pas le mot de la notice / pas dans la base) + 4 issues + bascule copilote ; « rien pour ce filtre » distingué | requête absurde → état complet ; requête filtrée → compte des autres types |
| `#/contrat` (+ `/slug`) | comprendre un contrat, travailler avec | ouvrir la fiche-espace de travail | fiche = jargon d'archivage + compteurs + mur de texte ; aucune action ; contexte perdu | haute | refonte chantier 3 | `f9671fd` : essentiel → mécanisme → travailler → preuves (« pourquoi ça compte ») → plus loin ; actions copilote/cas/RDV/argumentaire/comparer ; retour au contexte ; sélecteur en tuiles besoins | 5 contrats très différents testés + retours contexte + ancre exclusions + mobile |
| `#/comparateur` (+ `/a/b`) | décider entre deux contrats | comprendre ce qui change | juxtaposition de titres, orange sans explication, pas d'actions, pas de permutation | haute | refonte chantier 4 | `4e0db50` : ① 30 s (comparabilité + besoins doublon/complément/trou) ② apports propres + « favorable quand » ③ table ④ questions pour trancher ⑤ actions ; ⇄ ; contexte bidirectionnel | proches / non-comparables / complémentaires / lien profond / mobile |
| `#/copilote` | obtenir une base de réponse sourcée | poser la question | (chantier 1, déjà livré) | aucune | conserver | — (`1c5865d`) ; mémorise le contexte pour la fiche (`f9671fd`) | 3 questions + suivi + fiche→retour |
| `#/besoins` | analyser un cas client | cocher ce qu'on sait → diagnostic | formulaire figé objectifs→familles, sans statuts ni existant | haute | refonte chantier 5 | `374cf82` : divulgation progressive, déclaré/déduit/hypothèse, priorités expliquées, trous/doublons, candidats, expérience, synthèse | démos TNS + solo ; enchaînement RDV |
| `#/rdv` | préparer, mener, conclure un RDV | kit / notes / compte-rendu | seul l'« avant » existait, kit générique | haute | refonte chantier 6 | `abf6af9` : avant (kit inspecteur + cas repris) · pendant (accès nouvel onglet, notes marquées) · après (CR + mail générés des notes, 2ᵉ RDV) | parcours complet cas→kit→notes→CR testé |
| `#/argumentaire` | construire un support de vente | générer puis ADAPTER la trame | n'existait pas (texte à réciter ailleurs) | moyenne | créer chantier 7 | `aab016c` : trame/mail éditables, VALIDÉ-sourcé vs SUGGESTION-IA, [À COMPLÉTER], profils, retour aux preuves | trame TNS ≠ général ; mail ; régénérer |
| `#/glossaire` | vérifier un terme | filtrer, lire les définitions par contrat | aucune majeure (sourcé, filtré) | basse | conserver | — | filtre + sources OK |
| `#/pdf` | ouvrir la source qui fait foi | ouvrir une notice à la page | aucune majeure | basse | conserver | — | 11 documents listés, groupés |
| `#/decouvrir` | comprendre le produit | lire puis essayer | aucune majeure | basse | conserver | — | rend OK |
| `#/cas_usage` | voir ce que je peux faire | cliquer un exemple | cas client et argumentaire absents (nouvelles capacités invisibles) | basse | compléter | ce commit : +2 tuiles | rend OK |
| `#/premiers_pas` | apprendre les gestes | lire le guide | aucune majeure | basse | conserver | — | rend OK |
| `#/assistants` | donner Gabriel AXA à son IA | copier le mini-prompt | aucune majeure (protocole v2.1) | basse | conserver | — | copie + secours OK |
| `#/portail_ia` | explorer la Vue IA | ouvrir une brique | aucune majeure | basse | conserver | — | rend OK |
| `#/sources` | vérifier une règle publique | ouvrir l'autorité compétente | aucune majeure | basse | conserver | — | rend OK |
| `#/confiance` | vérifier la fiabilité | lire l'origine des données | aucune majeure | basse | conserver | — | rend OK |
| `#/tester` | participer au test | savoir quoi signaler | aucune majeure | basse | conserver | — | rend OK |
| `#/animateur` | former un conseiller | générer un brief | fonctionnel ; amélioration possible (lier aux fiches inspecteur) | basse | conserver, à revoir si usage réel | — | brief généré OK |
| `#/historique` | retrouver une recherche passée | relancer une ligne | **route morte** : retombait sur l'accueil sans le dire | haute | rendre routable | ce commit : routes hors-nav routables + lien « tout l'historique » (accueil) + aide | #/historique rend la page historique |
| `#/parametres` | maintenance (recharger, vider) | recharger les sources | **route morte** (idem) | moyenne | rendre routable | ce commit | #/parametres rend la page |
| `#/formulaires` | recueil local | ouvrir un formulaire | **route morte** (idem) | basse | rendre routable | ce commit | #/formulaires rend la page |
| `#/assistant` (singulier) | — (doublon historique d'`assistants`) | — | code mort trompeur | basse | supprimer | ce commit : fonction et route retirées | #/assistant → accueil (voulu) |

## Verdicts transverses

- **Aucune route sans statut** : 23 routes examinées, 4 refontes majeures (contrat, comparateur, besoins, rdv), 2 créations (argumentaire, accueil-intentions), 3 routes mortes réparées, 1 supprimée, 11 conservées en l'état.
- **Règle d'honnêteté appliquée partout** : toute interprétation issue du graphe porte « analyse IA · à valider » ; les faits sourcés renvoient à la notice ; les manques sont dits, jamais comblés.
- **Contexte** : recherche ↔ fiche ↔ comparateur ↔ cas ↔ RDV se conservent mutuellement (store `axaBack`, préremplissages).
- **Mobile** : chaque écran refondu vérifié à 375 px (0 débordement horizontal, grilles en 1 colonne).

*(Document d'audit — ne fait pas partie de l'app. La notice PDF fait foi.)*
