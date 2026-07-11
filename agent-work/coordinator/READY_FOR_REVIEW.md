# Prêt pour examen

_Généré le 2026-07-11T13:10:45Z. Lire CE fichier d'abord ; n'examiner que les éléments ci-dessous._

**Réel en attente : 8.** 8 contrôle(s)/trou(s) déjà transformé(s) en incidents structurés et sourcés : Claude examine les 5 éléments prioritaires (~24 min économisées) au lieu de refaire l'analyse.

## Haute priorité (résultats réels)
1. **quality** — quality__liens_internes_ia_valides (score 0.78)
   - fichier : `agent-work/quality/incidents/quality__liens_internes_ia_valides.json` · cible : `ia/`
   - risque : signal de qualité ; aucune correction appliquée automatiquement · action : vérification documentaire / correction manuelle
   - Contrôle qualité déterministe en échec (connue) : liens internes /ia valides — cassés: 19 ['glossaire.html -> contrat/essenciel.html', 'glossaire.html
2. **quality** — quality__notices_pdf_r_solues_sur_disque (score 0.78)
   - fichier : `agent-work/quality/incidents/quality__notices_pdf_r_solues_sur_disque.json` · cible : `ia/`
   - risque : signal de qualité ; aucune correction appliquée automatiquement · action : vérification documentaire / correction manuelle
   - Contrôle qualité déterministe en échec (connue) : notices PDF résolues sur disque — 0/11 résolues
3. **quality** — quality__preuves_avec_source_document_notice (score 0.78)
   - fichier : `agent-work/quality/incidents/quality__preuves_avec_source_document_notice.json` · cible : `ia/`
   - risque : signal de qualité ; aucune correction appliquée automatiquement · action : vérification documentaire / correction manuelle
   - Contrôle qualité déterministe en échec (connue) : preuves avec source (document/notice) — sans source: 6 /616
4. **quality** — quality__sorties_ia_publi_es_synchronis_es (score 0.78)
   - fichier : `agent-work/quality/incidents/quality__sorties_ia_publi_es_synchronis_es.json` · cible : `ia/`
   - risque : signal de qualité ; aucune correction appliquée automatiquement · action : vérification documentaire / correction manuelle
   - Contrôle qualité déterministe en échec (connue) : sorties /ia publiées synchronisées — désynchronisés: 146
5. **coverage** — coverage__categorie_absente_donnees_essen_ciel_assurance_obs_ques (score 0.73)
   - fichier : `agent-work/quality/incidents/coverage__categorie_absente_donnees_essen_ciel_assurance_obs_ques.json` · cible : `ia/matrices/couverture.json`
   - risque : ne signifie pas que la donnée manque dans le contrat : seulement absen · action : vérification documentaire humaine (donnée structurée manquante)
   - Contrat « Essen'Ciel (assurance obsèques) » : catégorie(s) definitions, conditions, declencheurs absente(s) des données structurées. — Constat sur DON

## Anomalies qualité
- **Nouvelles** : aucune
- **Connues** : sorties /ia publiées synchronisées, liens internes /ia valides, notices PDF résolues sur disque, preuves avec source (document/notice)
- **Corrigées** : aucune

## Régressions (tests de routage)
- aucune

## Changements de sources officielles
- aucun

## Conflits
- aucun

## Ordre recommandé
quality__liens_internes_ia_valides, quality__notices_pdf_r_solues_sur_disque, quality__preuves_avec_source_document_notice, quality__sorties_ia_publi_es_synchronis_es, coverage__categorie_absente_donnees_essen_ciel_assurance_obs_ques

## Extraction — tri de validation
- aucune proposition d'extraction en attente

## Extraction — rentabilité
Cette semaine : 0 pages analysées · 0 propositions · 0 retenues · ~0 min économisées.
Coût moyen : — tok/proposition utile · — tok/proposition acceptée. Contrat le + rentable : — · fournisseur : —.

---
Reprise : voir `agent-work/README.md` § « Reprise avec Claude ». Ne jamais relire tous les logs.
