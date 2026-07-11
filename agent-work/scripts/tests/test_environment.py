#!/usr/bin/env python3
"""Tests de la phase 4 (déterministe) : ancrage d'environnement réglementaire/fiscal dans le graphe.

Hors-ligne, 0 token, 0 réseau. Vérifie : autorités + concepts en DOMAINES SÉPARÉS, arêtes governed_by
concept→autorité et clause→concept (par recoupement de mots-clés), non-mélange des couches, idempotence,
montée de l'axe 'environment'.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import knowledge_graph as KG
import coverage_model as CM
import environment_ingest as EI


class FakeAdapter:
    domain_id = "axa-contrat"
    def environment_sources(self):
        return {
            "authorities": [
                {"id": "code-assurances", "nom": "Code des assurances", "url": "https://x", "type": "juridique",
                 "role": "droit", "as_of": "2026-07-10"},
                {"id": "bofip", "nom": "BOFiP", "url": "https://y", "type": "fiscal", "role": "doctrine",
                 "as_of": "2026-07-10"},
            ],
            "concepts": [
                {"key": "invalidite", "nom": "Invalidite", "domain": "reglementation",
                 "authorities": ["code-assurances"], "keywords": ["invalidite"], "as_of": "2026-07-10"},
                {"key": "fiscalite-vie", "nom": "Fiscalite assurance vie", "domain": "fiscalite",
                 "authorities": ["bofip"], "keywords": ["fiscalite", "succession"], "as_of": "2026-07-10"},
            ],
        }


def _graph():
    return KG.KnowledgeGraph("g.json", now=lambda: "2026-07-11T00:00:00Z")


class TestEnvironmentAnchoring(unittest.TestCase):
    def _seed_contract(self, g):
        # une garantie dont les mots-clés recoupent le concept 'invalidite'
        g.add_evidence("axa-contrat", "Avizen", "n.pdf", 16, "rente invalidite", "a")
        g.upsert_entity("axa-contrat", "Avizen", "garantie", "Rente invalidite",
                        content={"keywords": ["rente", "invalidite", "accident"]}, confidence=0.8)

    def test_separate_domains_and_gov_edges(self):
        g = _graph(); self._seed_contract(g)
        st = EI.ingest_environment(FakeAdapter(), g)
        self.assertEqual(st["authorities"], 2)
        self.assertEqual(st["concepts"], 2)
        # domaines bien séparés
        self.assertEqual(sorted({n["domain"] for n in g.nodes(layer=2)}),
                         ["axa-contrat", "fiscalite", "reglementation"])
        # concept -> autorité
        self.assertGreaterEqual(st["gov_concept_authority"], 2)
        # clause -> concept (recoupement de mots-clés 'invalidite')
        self.assertEqual(st["gov_clause_concept"], 1)

    def test_contract_entity_domain_unchanged(self):
        g = _graph(); self._seed_contract(g)
        EI.ingest_environment(FakeAdapter(), g)
        gar = [n for n in g.nodes(layer=2, domain="axa-contrat")][0]
        self.assertEqual(gar["domain"], "axa-contrat")     # jamais mélangé

    def test_environment_axis_rises(self):
        g = _graph(); self._seed_contract(g)
        before = CM.coverage_vector(g, "Avizen", "axa-contrat")["environment"]
        EI.ingest_environment(FakeAdapter(), g)
        after = CM.coverage_vector(g, "Avizen", "axa-contrat")["environment"]
        self.assertEqual(before, 0.0)
        self.assertEqual(after, 1.0)                        # ancrage réglementaire présent

    def test_idempotent(self):
        g = _graph(); self._seed_contract(g)
        EI.ingest_environment(FakeAdapter(), g)
        edges1 = len(g.data["edges"])
        st2 = EI.ingest_environment(FakeAdapter(), g)       # rerun
        self.assertEqual(len(g.data["edges"]), edges1)      # aucune arête en double
        self.assertEqual(st2["gov_clause_concept"], 0)      # rien de nouveau

    def test_no_match_no_clause_edge(self):
        g = _graph()
        g.upsert_entity("axa-contrat", "Autre", "garantie", "Capital deces",
                        content={"keywords": ["capital", "deces"]})   # aucun recoupement concept
        st = EI.ingest_environment(FakeAdapter(), g)
        self.assertEqual(st["gov_clause_concept"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
