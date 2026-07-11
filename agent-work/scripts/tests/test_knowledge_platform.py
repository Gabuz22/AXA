#!/usr/bin/env python3
"""Tests de la plateforme de connaissances : graphe en couches + couverture multi-dimensionnelle.

Hors-ligne, déterministe, sans LLM. Démontre : couches L1-L4, séparation des domaines + relations
transverses, dédup/idempotence, évidence append-only, mesure de PROFONDEUR, génération de tâches
d'approfondissement (relier/expliquer) même sur une entité déjà connue.
"""
import os, sys, json, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import coverage_model as CM


def _graph():
    return KG.KnowledgeGraph("kg.json", now=lambda: "2026-07-11T00:00:00Z")


class TestLayersAndDedup(unittest.TestCase):
    def test_evidence_append_only_and_dedup(self):
        g = _graph()
        n1 = g.add_evidence("axa-contrat", "Avizen", "notice.pdf", 5, "Le capital est verse au terme.", "cx")
        n2 = g.add_evidence("axa-contrat", "Avizen", "notice.pdf", 5, "Le capital est verse au terme.", "cx")
        self.assertEqual(n1["id"], n2["id"])                 # même preuve -> un seul nœud
        self.assertEqual(len([x for x in g.data["nodes"].values() if x["layer"] == 1]), 1)
        self.assertEqual(g.get_node(n1["id"])["times_seen"], 2)

    def test_entity_dedup_and_enrichment(self):
        g = _graph()
        e1, new1 = g.upsert_entity("axa-contrat", "Avizen", "garantie", "Capital deces",
                                   content={"resume": "v1"}, confidence=0.6)
        e2, new2 = g.upsert_entity("axa-contrat", "Avizen", "garantie", "Capital deces",
                                   content={"resume": "v2 enrichi"}, confidence=0.8)
        self.assertTrue(new1)
        self.assertEqual(e1["id"], e2["id"])                 # même identité
        self.assertEqual(e2["revision"], 2)                  # contenu enrichi -> révision
        self.assertEqual(e2["confidence"], 0.8)              # confiance = max

    def test_relation_dedup_and_validation(self):
        g = _graph()
        a, _ = g.upsert_entity("axa-contrat", "Avizen", "garantie", "A")
        b, _ = g.upsert_entity("axa-contrat", "Avizen", "exclusion", "B")
        _e, new1 = g.add_relation("excludes", a["id"], b["id"])
        _e, new2 = g.add_relation("excludes", a["id"], b["id"])
        self.assertTrue(new1); self.assertFalse(new2)        # arête dédupliquée
        with self.assertRaises(ValueError):
            g.add_relation("relation_bidon", a["id"], b["id"])

    def test_understanding_creates_explains_edge(self):
        g = _graph()
        e, _ = g.upsert_entity("axa-contrat", "Avizen", "garantie", "Capital deces")
        u, new = g.upsert_understanding(e["id"], "role", "Cette garantie protege les proches en cas de deces.")
        self.assertTrue(new)
        self.assertTrue(g.has_understanding(e["id"]))        # rattachement L4 -> L2


class TestDomainSeparation(unittest.TestCase):
    def test_domains_isolated_but_relatable(self):
        g = _graph()
        gar, _ = g.upsert_entity("axa-contrat", "Avizen", "garantie", "Rente education")
        loi, _ = g.upsert_entity("fiscalite", "Avizen", "regle", "Abattement succession")
        # les deux entités existent dans des DOMAINES distincts
        self.assertEqual(len(g.nodes(layer=2, domain="axa-contrat")), 1)
        self.assertEqual(len(g.nodes(layer=2, domain="fiscalite")), 1)
        # une relation transverse est possible (clause -> environnement) sans les mélanger
        e, new = g.add_relation("governed_by", gar["id"], loi["id"])
        self.assertTrue(new)
        self.assertEqual(g.get_node(gar["id"])["domain"], "axa-contrat")  # inchangé


class TestSupersede(unittest.TestCase):
    def test_supersede_marks_status(self):
        g = _graph()
        e, _ = g.upsert_entity("axa-contrat", "Avizen", "garantie", "Ancienne")
        g.supersede(e["id"], by_id="autre")
        self.assertEqual(g.get_node(e["id"])["status"], "superseded")
        self.assertEqual(g.nodes(layer=2, subject="Avizen"), [])   # exclu des actifs


class TestCoverageDepth(unittest.TestCase):
    def _seed_entity_only(self):
        g = _graph()
        g.add_evidence("axa-contrat", "Avizen", "n.pdf", 5, "Capital verse au terme.", "cx")
        g.upsert_entity("axa-contrat", "Avizen", "garantie", "Capital deces",
                        content={"resume": "x"}, confidence=0.7)
        return g

    def test_vector_reflects_missing_depth(self):
        g = self._seed_entity_only()
        v = CM.coverage_vector(g, "Avizen", "axa-contrat")
        self.assertEqual(v["evidence"], 1.0)
        self.assertEqual(v["normalized"], 1.0)
        self.assertEqual(v["relations"], 0.0)          # entité isolée
        self.assertEqual(v["understanding"], 0.0)      # pas d'explication

    def test_depth_increases_with_relations_and_understanding(self):
        g = self._seed_entity_only()
        d0 = CM.depth_score(CM.coverage_vector(g, "Avizen", "axa-contrat"))
        ent = g.nodes(layer=2, subject="Avizen")[0]
        other, _ = g.upsert_entity("axa-contrat", "Avizen", "exclusion", "Guerre")
        g.add_relation("excludes", ent["id"], other["id"])
        g.upsert_understanding(ent["id"], "role", "Protege les proches en cas de deces premature.")
        d1 = CM.depth_score(CM.coverage_vector(g, "Avizen", "axa-contrat"))
        self.assertGreater(d1, d0)                     # profondeur augmente sans nouvelle preuve

    def test_deepening_tasks_target_weak_axes_even_when_known(self):
        g = self._seed_entity_only()                   # entité CONNUE mais isolée
        res = CM.generate_deepening_tasks(g, "Avizen", "axa-contrat")
        types = {t["type"] for t in res["tasks"]}
        self.assertIn("relier", types)                 # approfondir : relier
        self.assertIn("expliquer", types)              # approfondir : expliquer
        # « comprendre mieux » génère du travail même sans phrase nouvelle à extraire

    def test_deepening_task_ids_stable_idempotent(self):
        g = self._seed_entity_only()
        r1 = CM.generate_deepening_tasks(g, "Avizen", "axa-contrat")
        r2 = CM.generate_deepening_tasks(g, "Avizen", "axa-contrat")
        self.assertEqual([t["task_id"] for t in r1["tasks"]], [t["task_id"] for t in r2["tasks"]])
        merged = {t["task_id"]: t for t in (r1["tasks"] + r2["tasks"])}
        self.assertEqual(len(merged), len(r1["tasks"]))   # aucun doublon

    def test_full_depth_generates_no_task(self):
        g = self._seed_entity_only()
        ent = g.nodes(layer=2, subject="Avizen")[0]
        other, _ = g.upsert_entity("axa-contrat", "Avizen", "exclusion", "Guerre")
        env, _ = g.upsert_entity("fiscalite", "Avizen", "regle", "Abattement")
        g.add_relation("excludes", ent["id"], other["id"])
        g.add_relation("governed_by", ent["id"], env["id"])
        g.add_relation("excludes", other["id"], ent["id"])
        g.upsert_understanding(ent["id"], "role", "Explication complete de la garantie et de son role.")
        g.upsert_understanding(other["id"], "role", "Explication de l'exclusion de guerre.")
        res = CM.generate_deepening_tasks(g, "Avizen", "axa-contrat", threshold=0.6)
        self.assertEqual(res["tasks"], [])             # tout au-dessus du seuil -> plus rien à approfondir


class TestPersistenceResilience(unittest.TestCase):
    def test_reload_preserves_graph(self):
        store = {}
        def wj(p, d, **k): store[p] = json.loads(json.dumps(d))
        def lj(p, default=None): return json.loads(json.dumps(store[p])) if p in store else default
        g = KG.KnowledgeGraph("kg.json", load_json=lj, write_json=wj, now=lambda: "2026-07-11T00:00:00Z")
        g.add_evidence("axa-contrat", "Avizen", "n.pdf", 5, "Preuve.", "cx")
        g.upsert_entity("axa-contrat", "Avizen", "garantie", "Capital")
        g.save()
        g2 = KG.KnowledgeGraph("kg.json", load_json=lj, write_json=wj)
        self.assertEqual(g2.stats()["evidence"], 1)
        self.assertEqual(g2.stats()["normalized"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
