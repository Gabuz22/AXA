# Prêt pour examen

_Généré le 2026-09-06T15:49:14Z. Lire CE fichier d'abord ; n'examiner que les éléments ci-dessous._

**Réel en attente : 76.** 76 contrôle(s)/trou(s) déjà transformé(s) en incidents structurés et sourcés : Claude examine les 5 éléments prioritaires (~228 min économisées) au lieu de refaire l'analyse.

## Haute priorité (résultats réels)
1. **extraction** — extraction_llm_20260711_171146_001 (score 0.90)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260711_171146_001.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : nouveau contrat
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel Patrimoine"] / conditions`
   - Définit la durée de validité de la prestation d'assistance.
2. **extraction** — extraction_llm_20260711_175433_001 (score 0.90)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260711_175433_001.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : categorie vide
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel (assurance obsèques)"] / definitions`
   - Ces concepts sont absents des définitions du contrat alors qu'ils sont souvent liés aux garanties de prévoyance.
3. **extraction** — extraction_llm_20260816_130347_001 (score 0.90)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260816_130347_001.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : categorie vide
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel Patrimoine"] / definitions`
   - Définit les bénéficiaires potentiels des services d'assistance.
4. **extraction** — extraction_llm_20260816_184938_001 (score 0.90)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260816_184938_001.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : nouveau contrat
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel Patrimoine"] / declencheurs`
   - Définit la période d'éligibilité temporelle après le décès.
5. **extraction** — extraction_llm_20260816_184938_002 (score 0.90)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260816_184938_002.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : nouveau contrat
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel Patrimoine"] / plafonds`
   - Définit la limite financière globale pour la garde d'enfants.

## Anomalies qualité
- **Nouvelles** : aucune
- **Connues** : sorties /ia publiées synchronisées, liens internes /ia valides, preuves avec source (document/notice)
- **Corrigées** : aucune

## Régressions (tests de routage)
- aucune

## Changements de sources officielles
- aucun

## Conflits
- aucun

## Ordre recommandé
extraction_llm_20260711_171146_001, extraction_llm_20260711_175433_001, extraction_llm_20260816_130347_001, extraction_llm_20260816_184938_001, extraction_llm_20260816_184938_002

## Extraction — tri de validation
- **rapide (<30 s)** : extraction_llm_20260711_173824_008 (30 s, prio haute) ; extraction_llm_20260711_005825_001 (30 s, prio ?) ; extraction_llm_20260816_070321_003 (30 s, prio haute) ; extraction_llm_20260711_005825_003 (30 s, prio ?) ; extraction_llm_20260723_084737_003 (30 s, prio haute) ; extraction_llm_20260711_172002_004 (30 s, prio haute)
- **moyenne** : extraction_llm_20260823_185112_004 (1 min, prio haute) ; extraction_llm_20260803_200209_003 (1 min, prio haute) ; extraction_llm_20260711_193533_001 (1 min, prio haute) ; extraction_llm_20260711_225806_003 (1 min, prio haute) ; extraction_llm_20260803_200211_004 (1 min, prio haute) ; extraction_llm_20260816_070321_002 (1 min, prio haute)
- **longue** : extraction_llm_20260803_200209_002 (2 min, prio moyenne) ; extraction_llm_20260711_193533_002 (2 min, prio haute) ; extraction_llm_20260712_135918_002 (2 min, prio haute) ; extraction_llm_20260711_173821_003 (2 min, prio moyenne) ; extraction_llm_20260711_173824_006 (2 min, prio moyenne) ; extraction_llm_20260712_193433_001 (2 min, prio moyenne)

## Extraction — rentabilité
Cette semaine : 0 pages analysées · 0 propositions · 0 retenues · ~0 min économisées.
Coût moyen : 4441 tok/proposition utile · — tok/proposition acceptée. Contrat le + rentable : Excelium (assurance vie) · fournisseur : gemini.

## Fournisseurs LLM (métriques)
- **gemini** : appels 1127 · succès 1114 · erreurs 12 · tok 762203/121028 · temps moy 1.38s

## Cycle d'orchestration (dernier)
- Déterministes exécutés : knowledge-curator, inspector-evaluator, coverage-gaps, quality
- Tâches faites ce cycle : 0 · en attente : 0
- Fournisseurs disponibles : gemini, groq, cloudflare, openrouter
- Fournisseurs au repos : claude-assisted-test→cle_absente (reprise ?)

---
Reprise : voir `agent-work/README.md` § « Reprise avec Claude ». Ne jamais relire tous les logs.
