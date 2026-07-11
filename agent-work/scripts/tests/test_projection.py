#!/usr/bin/env python3
"""Tests de la phase 9 : projection IA lecture seule depuis le graphe.

Déterministe, 0 token. Vérifie : couches séparées (preuve/normalisé/relation/interprétation/
environnement), provenance conservée, reconstructibilité (même graphe → même projection), et que
l'environnement/interprétation ne sont jamais mélangés aux clauses.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import knowledge_projection as KP


def _g():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")


def _seed(g):
    ev = g.add_evidence("axa-contrat", "Avizen", "notice.pdf", 16, "Le capital est verse au terme.", "extraction-llm")
    gar, _ = g.upsert_entity("axa-contrat", "Avizen", "garantie", "Capital deces",
                             content={"resume": "verse un capital"}, evidence_ids=[ev["id"]], confidence=0.8)
    exc, _ = g.upsert_entity("axa-contrat", "Avizen", "exclusion", "Guerre", confidence=0.3)  # incertaine
    g.add_relation("excludes", gar["id"], exc["id"], agent="knowledge-builder")
    g.upsert_understanding(gar["id"], "role", "Protege les proches en cas de deces.", agent="knowledge-builder")
    env, _ = g.upsert_entity("reglementation", "Avizen", "concept_reglementaire", "Deces")
    g.add_relation("governed_by", gar["id"], env["id"], agent="environment-ingest")
    return g


class TestProjection(unittest.TestCase):
    def test_layers_separated(self):
        g = _seed(g=_g())
        p = KP.project_subject(g, "Avizen", "axa-contrat", expected=["garantie", "exclusion"])
        # L2 par catégorie
        self.assertIn("garantie", p["connaissances"])
        self.assertIn("exclusion", p["connaissances"])
        # L3 relations internes (pas governed_by, pas explains)
        self.assertTrue(any(r["type"] == "excludes" for r in p["relations"]))
        self.assertFalse(any(r["type"] in ("governed_by", "explains") for r in p["relations"]))
        # environnement séparé
        self.assertTrue(p["environnement"])
        self.assertEqual(p["environnement"][0]["domaine"], "reglementation")
        # interprétation (L4) séparée et étiquetée
        self.assertTrue(p["comprehension"])
        self.assertEqual(p["comprehension"][0]["nature"], "interpretation")

    def test_provenance_preserved(self):
        g = _seed(g=_g())
        p = KP.project_subject(g, "Avizen", "axa-contrat")
        gar = p["connaissances"]["garantie"][0]
        self.assertTrue(gar["sources"])
        self.assertEqual(gar["sources"][0]["document"], "notice.pdf")
        self.assertEqual(gar["sources"][0]["page"], 16)
        # preuves L1 présentes
        self.assertTrue(p["preuves"])

    def test_uncertainty_surfaced(self):
        g = _seed(g=_g())
        p = KP.project_subject(g, "Avizen", "axa-contrat")
        self.assertTrue(any(i["label"] == "Guerre" for i in p["incertitudes"]))

    def test_reconstructible(self):
        g = _seed(g=_g())
        p1 = KP.project_subject(g, "Avizen", "axa-contrat")
        p2 = KP.project_subject(g, "Avizen", "axa-contrat")
        self.assertEqual(p1, p2)                        # fonction pure du graphe

    def test_fingerprint_changes_with_graph(self):
        g = _seed(g=_g())
        f1 = KP.graph_fingerprint(g)
        g.upsert_entity("axa-contrat", "Avizen", "option", "Exoneration")
        self.assertNotEqual(f1, KP.graph_fingerprint(g))


if __name__ == "__main__":
    unittest.main(verbosity=2)
