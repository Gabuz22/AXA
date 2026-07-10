# Prêt pour examen

_Généré le 2026-07-10T19:56:14Z par le coordinateur. Lire CE fichier d'abord ; n'examiner que les éléments ci-dessous._

**En attente : 8 proposition(s).** 8 micro-zones déjà transformées en propositions sourcées et structurées : Claude examine ces 5 éléments prioritaires au lieu de refaire l'analyse préparatoire.

## Haute priorité
1. **official-source** — official_sources_20260710_194415_001 (score 0.93, confiance 0.9)
   - fichier proposition : `agent-work/official-sources/pending/official_sources_20260710_194415_001.json`
   - cible : `ia/sources-officielles.json` · **réglementaire → validation humaine**
   - Exemple de detection de changement d'empreinte (aucun reseau). Aucune interpretation reglementaire.
2. **quality** — quality_20260710_194449_001 (score 0.78, confiance 0.99)
   - fichier proposition : `agent-work/quality/incidents/quality_20260710_194449_001.json`
   - cible : `ia/`
   - Contrôle qualité déterministe en échec : liens internes /ia valides — cassés: 19 ['glossaire.html -> contrat/essenciel.html', 'glossaire.html -> contrat/ma-prot
3. **quality** — quality_20260710_194449_002 (score 0.78, confiance 0.99)
   - fichier proposition : `agent-work/quality/incidents/quality_20260710_194449_002.json`
   - cible : `ia/`
   - Contrôle qualité déterministe en échec : notices PDF résolues sur disque — 0/11 notices résolues
4. **adversarial-test** — adversarial_tests_20260710_194416_001 (score 0.68, confiance 0.8)
   - fichier proposition : `agent-work/tests/pending/adversarial_tests_20260710_194416_001.json`
   - cible : `ia/tests.json`
   - Question adversariale pour eprouver le routage (negation). Resultat attendu fourni ; moteur non modifie.
5. **adversarial-test** — adversarial_tests_20260710_194416_002 (score 0.67, confiance 0.78)
   - fichier proposition : `agent-work/tests/pending/adversarial_tests_20260710_194416_002.json`
   - cible : `ia/tests.json`
   - Question adversariale pour eprouver le routage (comparaison_implicite). Resultat attendu fourni ; moteur non modifie.

## Tests nouveaux (à exécuter contre le moteur)
- 2 proposition(s) de test ; familles : comparaison_implicite, negation

## Changements de sources officielles
- official_sources_20260710_194415_001 — statut `changement_technique` — https://www.service-public.fr/ (interprétation NON effectuée)

## Conflits
- _(aucun)_

## Ordre recommandé
official_sources_20260710_194415_001, quality_20260710_194449_001, quality_20260710_194449_002, adversarial_tests_20260710_194416_001, adversarial_tests_20260710_194416_002

---
Protocole de reprise : voir `agent-work/README.md` § « Reprise du projet avec Claude ». Ne jamais demander à Claude de relire tous les logs.
