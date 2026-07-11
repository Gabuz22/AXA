#!/usr/bin/env python3
"""Tests des phases 11-13 : banc d'essai + évaluateur déterministe + boucle échec→tâche. 0 token."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import inspector_bench as IB


def _graph():
    g = KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")
    g.add_evidence("axa-contrat", "Avizen", "n.pdf", 5, "cit", "a")
    g.upsert_entity("axa-contrat", "Avizen", "garantie", "Rente invalidite (principale)", content={"keywords": ["invalidite"]})
    g.upsert_entity("axa-contrat", "Avizen", "exclusion", "Guerre")
    g.upsert_entity("axa-contrat", "Avizen", "condition", "Taux >= 11%")
    g.upsert_entity("axa-contrat", "Excelium", "garantie", "Epargne", content={"keywords": ["epargne"]})
    return g


class TestBench(unittest.TestCase):
    def test_run_bench_scores_all_families(self):
        g = _graph()
        rep = IB.run_bench(g, "axa-contrat", ["Avizen", "Excelium"])
        self.assertEqual(rep["n_tests"], len(IB.default_bench(["Avizen", "Excelium"])))
        self.assertGreaterEqual(rep["score_global"], 0.0)
        self.assertLessEqual(rep["score_global"], 1.0)
        for fam in ("mono", "multi", "cas_mono", "cas_multi"):
            self.assertIn(fam, rep["score_par_famille"])

    def test_evaluator_catches_invention(self):
        g = _graph()
        # réponse falsifiée : cite une garantie inexistante
        fake = {"kind": "cas_mono", "answer": {"clauses_potentiellement_pertinentes": ["Garantie fantome inexistante"],
                                               "elements_cas_pertinents": {}, "hypotheses": {},
                                               "donnees_manquantes": ["x"], "conclusion_provisoire": "provisoire",
                                               "validation_humaine_requise": True}}
        card = IB.evaluate({"id": "t", "family": "cas_mono"}, fake, g, "axa-contrat")
        self.assertFalse(card["checks"]["aucune_invention"])
        self.assertIn("aucune_invention", card["failures"])

    def test_no_match_case_says_idk(self):
        g = _graph()
        import inspector_case as IC
        case = IC.new_case(besoins_exprimes=["assurance automobile"])
        test = {"id": "nm", "family": "cas_mono", "subject": "Avizen", "case": case, "expect_no_match": True}
        r = IB.run_test(test, g, "axa-contrat", ["Avizen"])
        card = IB.evaluate(test, r, g, "axa-contrat")
        self.assertTrue(card["checks"]["dit_je_ne_sais_pas"])

    def test_diagnose_creates_tasks(self):
        card = {"test": "t", "failures": ["aucune_invention", "conclusion_conditionnelle"]}
        tasks = IB.diagnose(card)
        self.assertEqual(len(tasks), 2)
        self.assertTrue(all("type" in t and "cause" in t for t in tasks))

    def test_clean_case_scores_well(self):
        g = _graph()
        rep = IB.run_bench(g, "axa-contrat", ["Avizen", "Excelium"])
        # les cas déterministes bien formés doivent avoir un score global décent
        self.assertGreater(rep["score_global"], 0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
