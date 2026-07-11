#!/usr/bin/env python3
"""Tests des phases 10 (reviewer hiérarchisé) et 11 (manager stratégique). Déterministe, 0 token."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import knowledge_review as KR
import knowledge_manager as KM


def _g():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")


class TestReviewer(unittest.TestCase):
    def test_non_sensitive_high_conf_auto(self):
        g = _g()
        ev = g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "cit", "a")
        n, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "Capital",
                               evidence_ids=[ev["id"]], confidence=0.9)
        a = KR.assess_node(g, g.get_node(n["id"]))
        self.assertEqual(a["escalate"], "auto")            # non sensible + confiant -> pas d'humain

    def test_sensitive_goes_to_model_or_human(self):
        g = _g()
        n, _ = g.upsert_entity("axa-contrat", "C1", "exclusion", "Guerre exclue", confidence=0.9)
        a = KR.assess_node(g, g.get_node(n["id"]))
        self.assertIn(a["escalate"], ("model", "human"))   # exclusion = sensible
        self.assertTrue(a["sensitive"])

    def test_montant_is_sensitive(self):
        g = _g()
        n, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "Capital",
                               content={"resume": "capital de 100 000 €"}, confidence=0.9)
        self.assertTrue(KR.is_sensitive(g.get_node(n["id"])))

    def test_sensitive_low_conf_is_human_priority(self):
        g = _g()
        n, _ = g.upsert_entity("axa-contrat", "C1", "plafond", "Plafond 30%", confidence=0.3)
        a = KR.assess_node(g, g.get_node(n["id"]))
        self.assertEqual(a["escalate"], "human")
        self.assertGreaterEqual(a["priority"], 5)

    def test_review_graph_reduces_human_volume(self):
        g = _g()
        for i in range(8):
            g.upsert_entity("axa-contrat", "C1", "garantie", "Gar%d" % i, confidence=0.9)  # auto
        g.upsert_entity("axa-contrat", "C1", "exclusion", "Exclusion X", confidence=0.4)   # humain/model
        rep = KR.review_graph(g, "axa-contrat")
        self.assertGreater(rep["auto"], rep["human"])      # la majorité est auto-validable
        self.assertGreater(rep["auto_ratio"], 0.5)
        self.assertTrue(all(it["escalate"] != "auto" for it in rep["queue"]))


class TestManager(unittest.TestCase):
    def test_recommendations_from_metrics(self):
        store = {
            "agent-work/knowledge/coverage.json": {"subjects": {
                "Faible": {"depth_score": 0.3, "weak_axes": ["relations", "understanding"], "semantic_coverage": 0.4},
                "Fort": {"depth_score": 0.95, "weak_axes": [], "semantic_coverage": 1.0}}},
            "agent-work/knowledge/tasks.json": {"tasks": [
                {"task_id": "t1", "type": "relier", "status": "pending", "subject": "Faible", "first_seen": "2026-01-01"},
                {"task_id": "t2", "type": "relier", "status": "pending", "subject": "Faible", "first_seen": "2026-02-01"}]},
        }
        def lj(p, default=None): return store.get(p, default)
        def rp(x): return x
        rep = KM.analyze(lj, rp, "axa-contrat")
        # sujet le plus faible en tête
        self.assertEqual(rep["subjects_ranked"][0]["subject"], "Faible")
        types = {r["type"] for r in rep["recommendations"]}
        self.assertIn("approfondir", types)                # cible le sujet faible
        self.assertIn("prioriser_tache", types)            # type dominant 'relier'
        # jamais de modification : recommandations seulement
        self.assertIn("recommandations", rep["note"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
