#!/usr/bin/env python3
"""Tests de la phase 3 : capacités LLM d'approfondissement (L3 relations, L4 compréhension) + cycle de vie
du backlog. LLM factice injecté → hors-ligne, déterministe. Vérifie : relations valides ajoutées, garde-fous
(pas d'entité inventée, types validés), garde déterministe « déjà fait » (aucun appel LLM), explications L4,
réconciliation pending→resolved quand la lacune est comblée.
"""
import os, sys, json, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import knowledge_build as KB
import knowledge_tasks as KT
import coverage_model as CM


def _graph():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")


def _seed(g, n=3):
    g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "Le capital est verse au terme.", "a")
    labels = ["Capital deces", "Rente education", "Exclusion guerre"][:n]
    subs = ["garantie", "garantie", "exclusion"][:n]
    return [g.upsert_entity("axa-contrat", "C1", subs[i], labels[i])[0] for i in range(n)]


class TestBuildRelations(unittest.TestCase):
    def test_valid_relations_added(self):
        g = _graph(); _seed(g)
        def fake(prompt):
            return {"relations": [{"src": 0, "dst": 2, "type": "excludes", "confidence": 0.8},
                                  {"src": 0, "dst": 1, "type": "complements"}]}
        r = KB.build_relations(g, "axa-contrat", "C1", fake)
        self.assertEqual(r["added"], 2)
        self.assertEqual(g.stats()["relations"], 2)

    def test_guardrails_reject_invalid(self):
        g = _graph(); _seed(g)
        def fake(prompt):
            return {"relations": [
                {"src": 0, "dst": 0, "type": "excludes"},          # boucle -> rejet
                {"src": 0, "dst": 9, "type": "excludes"},          # indice inexistant -> rejet (pas d'invention)
                {"src": 0, "dst": 1, "type": "relation_bidon"},    # type inconnu -> rejet
                {"src": 1, "dst": 2, "type": "comparable_to"},     # valide
            ]}
        r = KB.build_relations(g, "axa-contrat", "C1", fake)
        self.assertEqual(r["added"], 1)

    def test_already_related_skips_llm(self):
        g = _graph(); ents = _seed(g)
        # relie chaque entité au moins une fois
        g.add_relation("comparable_to", ents[0]["id"], ents[1]["id"])
        g.add_relation("comparable_to", ents[2]["id"], ents[0]["id"])
        calls = {"n": 0}
        def fake(prompt):
            calls["n"] += 1; return {"relations": []}
        r = KB.build_relations(g, "axa-contrat", "C1", fake)
        self.assertEqual(r.get("skipped"), "already_related")
        self.assertEqual(calls["n"], 0)                            # AUCUN appel LLM : économie


class TestBuildUnderstanding(unittest.TestCase):
    def test_understanding_added_then_skipped(self):
        g = _graph(); _seed(g, n=1)
        def fake(prompt):
            return {"aspect": "role", "explanation": "Cette garantie verse un capital au deces.", "confidence": 0.7}
        r1 = KB.build_understanding(g, "axa-contrat", "C1", fake, max_entities=4)
        self.assertEqual(r1["added"], 1)
        self.assertEqual(g.stats()["understanding"], 1)
        calls = {"n": 0}
        def fake2(prompt):
            calls["n"] += 1; return {"explanation": "x"}
        r2 = KB.build_understanding(g, "axa-contrat", "C1", fake2)
        self.assertEqual(r2.get("skipped"), "all_explained")
        self.assertEqual(calls["n"], 0)                            # déjà expliqué -> pas d'appel

    def test_empty_explanation_not_written(self):
        g = _graph(); _seed(g, n=1)
        r = KB.build_understanding(g, "axa-contrat", "C1", lambda p: {"explanation": "   "})
        self.assertEqual(r["added"], 0)
        self.assertEqual(g.stats()["understanding"], 0)


class TestBacklogLifecycle(unittest.TestCase):
    def _store(self):
        store = {}
        def wj(p, d, **k): store[p] = json.loads(json.dumps(d))
        def lj(p, default=None): return json.loads(json.dumps(store[p])) if p in store else default
        return store, lj, wj

    def test_gap_resolved_after_deepening(self):
        g = _graph(); ents = _seed(g)
        store, lj, wj = self._store()
        # 1) le curateur génère : 'relier' est pending (relations = 0)
        t1 = KT.generate(g, "axa-contrat", ["C1"])
        KT.persist(t1, lj, wj, lambda: "t0")
        self.assertTrue(KT.pending(KT.load_backlog(lj), types=("relier",)))
        # 2) le bâtisseur relie toutes les entités
        def fake(prompt):
            return {"relations": [{"src": 0, "dst": 1, "type": "comparable_to"},
                                  {"src": 0, "dst": 2, "type": "excludes"},
                                  {"src": 1, "dst": 2, "type": "comparable_to"}]}
        KB.build_relations(g, "axa-contrat", "C1", fake)
        # 3) au passage suivant du curateur, l'axe 'relations' est couvert -> tâche 'relier' RÉSOLUE
        t2 = KT.generate(g, "axa-contrat", ["C1"])
        KT.persist(t2, lj, wj, lambda: "t1")
        self.assertEqual(KT.pending(KT.load_backlog(lj), types=("relier",)), [])
        relier = [t for t in KT.load_backlog(lj)["tasks"] if t["type"] == "relier"][0]
        self.assertEqual(relier["status"], "resolved")

    def test_reopened_when_new_entity_lowers_coverage(self):
        g = _graph(); ents = _seed(g, n=2)
        store, lj, wj = self._store()
        g.add_relation("comparable_to", ents[0]["id"], ents[1]["id"])
        KT.persist(KT.generate(g, "axa-contrat", ["C1"]), lj, wj, lambda: "t0")
        # les 2 entités sont reliées -> 'relier' résolu/absent
        self.assertEqual(KT.pending(KT.load_backlog(lj), types=("relier",)), [])
        # de nouvelles entités NON reliées apparaissent -> couverture 'relations' repasse sous le seuil
        g.upsert_entity("axa-contrat", "C1", "option", "Exoneration cotisations")
        g.upsert_entity("axa-contrat", "C1", "exclusion", "Faute intentionnelle")
        KT.persist(KT.generate(g, "axa-contrat", ["C1"]), lj, wj, lambda: "t1")
        self.assertTrue(KT.pending(KT.load_backlog(lj), types=("relier",)))   # rouvert automatiquement


if __name__ == "__main__":
    unittest.main(verbosity=2)
