#!/usr/bin/env python3
"""Tests de la phase 2 : passes déterministes + génération du backlog de tâches de connaissance.

Hors-ligne, déterministe, zéro token. Couvre : doublons, fraîcheur (TTL), candidats de contradiction,
cost-ledger, génération unifiée de tâches (approfondissement + opérations), persistance idempotente.
"""
import os, sys, json, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import knowledge_ops as KO
import knowledge_tasks as KT


def _graph(now="2026-07-11T00:00:00Z"):
    return KG.KnowledgeGraph("g.json", now=lambda: now)


class TestDeterministicOps(unittest.TestCase):
    def test_find_duplicates(self):
        g = _graph()
        g.upsert_entity("d", "C1", "garantie", "Capital deces")
        g.upsert_entity("d", "C1", "garantie", "Capital-deces")      # quasi-doublon (ponctuation) : id canonique distinct
        g.upsert_entity("d", "C1", "garantie", "Rente education")    # distincte
        dups = KO.find_duplicates(g, "d")
        self.assertEqual(len(dups), 1)

    def test_find_stale(self):
        g = _graph()
        fresh = g.add_evidence("d", "C1", "n.pdf", 1, "frais", "a", ttl_days=None)
        stale = g.add_evidence("d", "C1", "n.pdf", 2, "vieux", "a", as_of="2020-01-01T00:00:00Z", ttl_days=30)
        stale["freshness"]["checked_at"] = "2020-01-01T00:00:00Z"
        ids = KO.find_stale(g, now="2026-07-11T00:00:00Z")
        self.assertIn(stale["id"], ids)
        self.assertNotIn(fresh["id"], ids)

    def test_contradiction_candidates(self):
        g = _graph()
        g.upsert_entity("d", "C1", "garantie", "Garantie deces accident")
        g.upsert_entity("d", "C1", "exclusion", "sont exclus les deces par accident de guerre")
        cand = KO.find_contradiction_candidates(g, "C1", "d")
        self.assertEqual(len(cand), 1)

    def test_cost_ledger_gate(self):
        led = KO.CostLedger("c.json", now_week=lambda: "2026-W28")
        self.assertTrue(led.can_spend("axa-contrat", 5))
        for _ in range(5):
            led.record("axa-contrat", llm_calls=1, tokens=100)
        self.assertFalse(led.can_spend("axa-contrat", 5))     # plafond hebdo atteint
        self.assertEqual(led.used("axa-contrat")["tokens"], 500)


class TestTaskGeneration(unittest.TestCase):
    def _seed(self):
        g = _graph()
        g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "preuve", "a")
        g.upsert_entity("axa-contrat", "C1", "garantie", "Capital deces", confidence=0.7)
        return g

    def test_generate_deepening_and_operations(self):
        g = self._seed()
        # ajoute un quasi-doublon (ponctuation) pour déclencher une tâche 'dedup'
        g.upsert_entity("axa-contrat", "C1", "garantie", "Capital-deces", confidence=0.6)
        tasks = KT.generate(g, "axa-contrat", ["C1"])
        types = {t["type"] for t in tasks}
        self.assertIn("relier", types)        # profondeur
        self.assertIn("expliquer", types)
        self.assertIn("dedup", types)          # opération
        kinds = {t["kind"] for t in tasks}
        self.assertEqual(kinds, {"deepening", "operation"})

    def test_persist_idempotent(self):
        g = self._seed()
        tasks = KT.generate(g, "axa-contrat", ["C1"])
        store = {}
        def wj(p, d, **k): store[p] = json.loads(json.dumps(d))
        def lj(p, default=None): return json.loads(json.dumps(store[p])) if p in store else default
        total1, new1 = KT.persist(tasks, lj, wj, lambda: "t0")
        total2, new2 = KT.persist(tasks, lj, wj, lambda: "t1")     # rerun
        self.assertEqual(new1, total1)
        self.assertEqual(new2, 0)              # aucun doublon au second passage
        self.assertEqual(total1, total2)

    def test_summary_counts(self):
        g = self._seed()
        s = KT.summary(KT.generate(g, "axa-contrat", ["C1"]))
        self.assertEqual(s["total"], sum(s["by_type"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
