#!/usr/bin/env python3
"""Tests de la phase 2 : modèle de connaissance stabilisé (champs complets, validation, migration).

Vérifie : les nouveaux nœuds/arêtes portent tous les champs requis ; validate_node/edge/graph
détectent les manques ; migrate() complète les anciens éléments de façon idempotente et sans écraser.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG


def _g():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")


class TestNodeFields(unittest.TestCase):
    def test_new_nodes_carry_required_fields(self):
        g = _g()
        ev = g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "cit", "a")
        ent, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "Capital")
        for n in (ev, ent):
            ok, errs = KG.validate_node(n)
            self.assertTrue(ok, errs)
            for k in ("version", "validations", "ambiguities", "risks", "provenance_agent", "freshness"):
                self.assertIn(k, n)

    def test_new_edges_carry_sens_and_validation(self):
        g = _g()
        a, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "A")
        b, _ = g.upsert_entity("axa-contrat", "C1", "exclusion", "B")
        e, _ = g.add_relation("excludes", a["id"], b["id"], agent="knowledge-builder")
        ok, errs = KG.validate_edge(e)
        self.assertTrue(ok, errs)
        self.assertIn("directed", e)
        self.assertTrue(e["validation_required"])            # relation interprétée -> revue requise

    def test_structural_explains_not_validation_required(self):
        g = _g()
        ent, _ = g.upsert_entity("axa-contrat", "C1", "garantie", "A")
        g.upsert_understanding(ent["id"], "role", "Explication.")
        expl = [e for e in g.data["edges"].values() if e["type"] == "explains"][0]
        self.assertFalse(expl["validation_required"])        # lien structurel déterministe


class TestValidation(unittest.TestCase):
    def test_validate_detects_missing_and_bad(self):
        bad = {"id": "x", "layer": 3, "type": "entity", "status": "weird", "confidence": 2.0}
        ok, errs = KG.validate_node(bad)
        self.assertFalse(ok)
        self.assertTrue(any("layer" in e for e in errs))
        self.assertTrue(any("status" in e for e in errs))
        self.assertTrue(any("confidence" in e for e in errs))

    def test_validate_graph_reports_ok(self):
        g = _g()
        g.add_evidence("axa-contrat", "C1", "n.pdf", 5, "cit", "a")
        g.upsert_entity("axa-contrat", "C1", "garantie", "Capital")
        rep = KG.validate_graph(g)
        self.assertTrue(rep["ok"], rep["sample"])


class TestMigration(unittest.TestCase):
    def test_migrate_completes_old_nodes_idempotent(self):
        g = _g()
        # simule un nœud ANCIEN (avant phase 2) sans les nouveaux champs
        g.data["nodes"]["old1"] = {"id": "old1", "layer": 2, "type": "entity", "domain": "axa-contrat",
                                   "subject": "C1", "subtype": "garantie", "label": "X", "confidence": 0.6,
                                   "freshness": {"as_of": "d", "checked_at": "d"}, "content_hash": "h",
                                   "status": "active", "created_at": "d", "revision": 3}
        g.data["edges"]["olde"] = {"id": "olde", "layer": 3, "type": "excludes", "src": "old1", "dst": "old1",
                                   "confidence": 0.5, "status": "active", "created_at": "d"}
        n1 = KG.migrate(g)
        self.assertGreaterEqual(n1, 2)
        node = g.data["nodes"]["old1"]
        self.assertEqual(node["version"], 3)                 # dérivé de revision, non écrasé
        self.assertEqual(node["validations"], [])
        edge = g.data["edges"]["olde"]
        self.assertIn("directed", edge)
        self.assertTrue(edge["validation_required"])         # 'excludes' -> revue
        # idempotent : 2e passage ne modifie plus rien
        self.assertEqual(KG.migrate(g), 0)

    def test_migrate_does_not_overwrite(self):
        g = _g()
        g.data["nodes"]["n"] = {"id": "n", "layer": 2, "type": "entity", "domain": "d", "subject": "s",
                                "confidence": 0.5, "freshness": {}, "content_hash": "h", "status": "active",
                                "created_at": "d", "validations": [{"level": 1}], "version": 9}
        KG.migrate(g)
        self.assertEqual(g.data["nodes"]["n"]["version"], 9)          # inchangé
        self.assertEqual(g.data["nodes"]["n"]["validations"], [{"level": 1}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
