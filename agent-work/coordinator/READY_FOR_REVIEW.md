# Prêt pour examen

_Généré le 2026-07-24T10:27:34Z. Lire CE fichier d'abord ; n'examiner que les éléments ci-dessous._

**Réel en attente : 56.** 56 contrôle(s)/trou(s) déjà transformé(s) en incidents structurés et sourcés : Claude examine les 5 éléments prioritaires (~168 min économisées) au lieu de refaire l'analyse.

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
3. **extraction** — extraction_llm_20260711_171146_003 (score 0.88)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260711_171146_003.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : nouveau contrat
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel Patrimoine"] / conditions`
   - Définit la période d'éligibilité au service.
4. **extraction** — extraction_llm_20260711_172002_003 (score 0.88)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260711_172002_003.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : nouveau contrat
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel Patrimoine"] / conditions`
   - Définit une condition temporelle pour la sortie du contrat.
5. **extraction** — extraction_llm_20260711_172002_004 (score 0.88)
   - fichier : `agent-work/extraction/pending/extraction_llm_20260711_172002_004.json` · cible : `data/AXA/AXA_MASTER_DONNEES_PACK_A_STABLE.json`
   - risque : validation notice PDF obligatoire ; master jamais modifie · action : revue humaine
   - ⏱ validation ~30 s · importance moyenne · confiance 0.95 · pourquoi : nouveau contrat
   - cible master : `AXA_MASTER_DONNEES_PACK_A_STABLE.json :: contrat["Essen'Ciel Patrimoine"] / definitions`
   - Définit le mécanisme de maintien des garanties en cas d'arrêt de paiement.

## Anomalies qualité
- **Nouvelles** : aucune
- **Connues** : sorties /ia publiées synchronisées, preuves avec source (document/notice)
- **Corrigées** : aucune

## Régressions (tests de routage)
- aucune

## Changements de sources officielles
- aucun

## Conflits
- aucun

## Ordre recommandé
extraction_llm_20260711_171146_001, extraction_llm_20260711_175433_001, extraction_llm_20260711_171146_003, extraction_llm_20260711_172002_003, extraction_llm_20260711_172002_004

## Extraction — tri de validation
- **rapide (<30 s)** : extraction_llm_20260711_173821_002 (30 s, prio haute) ; extraction_llm_20260710_222422_002 (30 s, prio ?) ; extraction_llm_20260711_173824_007 (30 s, prio haute) ; extraction_llm_20260711_005825_004 (30 s, prio ?) ; extraction_llm_20260711_005825_005 (30 s, prio ?) ; extraction_llm_20260711_173821_005 (30 s, prio haute)
- **moyenne** : extraction_llm_20260711_172002_002 (1 min, prio haute) ; extraction_llm_20260713_195318_006 (1 min, prio haute) ; extraction_llm_20260713_195313_002 (1 min, prio haute) ; extraction_llm_20260711_225806_002 (1 min, prio haute) ; extraction_llm_20260711_173821_001 (1 min, prio haute) ; extraction_llm_20260712_135918_003 (1 min, prio haute)
- **longue** : extraction_llm_20260711_173824_006 (2 min, prio moyenne) ; extraction_llm_20260712_193433_002 (2 min, prio haute) ; extraction_llm_20260711_171150_005 (2 min, prio moyenne) ; extraction_llm_20260711_175435_002 (2 min, prio moyenne) ; extraction_llm_20260712_083339_001 (2 min, prio haute) ; extraction_llm_20260712_193433_001 (2 min, prio moyenne)

## Extraction — rentabilité
Cette semaine : 75 pages analysées · 26 propositions · 8 retenues · ~1h36 économisées.
Coût moyen : 3303 tok/proposition utile · — tok/proposition acceptée. Contrat le + rentable : Essen'Ciel (assurance obsèques) · fournisseur : gemini.

## Fournisseurs LLM (métriques)
- **gemini** : appels 309 · succès 300 · erreurs 9 · tok 258129/42701 · temps moy 0.87s

## Cycle d'orchestration (dernier)
- Déterministes exécutés : knowledge-curator, inspector-evaluator, coverage-gaps, quality
- Tâches faites ce cycle : 0 · en attente : 0
- Fournisseurs disponibles : gemini, groq, cloudflare, openrouter
- Fournisseurs au repos : claude-assisted-test→cle_absente (reprise ?)

---
Reprise : voir `agent-work/README.md` § « Reprise avec Claude ». Ne jamais relire tous les logs.
