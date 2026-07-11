#!/usr/bin/env python3
"""Tests de l'explorateur de corpus (moteur générique corpus_intel + carte de couverture).

Hors-ligne, déterministe : aucun PDF, aucun réseau, aucun LLM réel (llm_fn factice injectable).
Couvre : reprise après interruption, PDF modifié, zone inchangée (skip), zone nouvelle, création de
tâches typées, absence de doublons, couverture progressive, aucun retraitement inutile.
"""
import os, sys, json, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import corpus_intel as CI


def _mem_store():
    store = {}
    def wj(path, data, **kw):
        store[path] = json.loads(json.dumps(data))
    def lj(path, default=None):
        return json.loads(json.dumps(store[path])) if path in store else default
    return store, lj, wj


# Pages synthétiques d'une notice fictive (générique, aucun contenu réel).
PAGES = {
    1: "NOTICE D'INFORMATION Contrat Modele",
    2: "Sommaire table des matieres",
    3: "Definitions : on entend par Beneficiaire la personne designee. Capital Garanti defini ici.",
    4: "Definitions suite. Franchise applicable.",
    5: "Garanties : nous garantissons le versement d'un Capital Garanti. Rente Education proposee.",
    6: "Exclusions : sont exclus les faits de Guerre Civile et la Faute Intentionnelle.",
}
LABEL_RULES = [
    ("sommaire", ["sommaire", "table des matieres"]),
    ("definitions", ["definition", "on entend par"]),
    ("garanties", ["garantie", "nous garantissons", "capital"]),
    ("exclusions", ["exclusion", "sont exclus"]),
    ("titre", ["notice"]),
]


class TestCartographyZoning(unittest.TestCase):
    def test_cartography_labels_pages(self):
        carto = CI.cartography(PAGES, LABEL_RULES)
        self.assertEqual(carto[2], "sommaire")
        self.assertEqual(carto[3], "definitions")
        self.assertEqual(carto[6], "exclusions")

    def test_segment_merges_consecutive(self):
        carto = CI.cartography(PAGES, LABEL_RULES)
        zones = CI.segment_zones(carto)
        defz = [z for z in zones if z["label"] == "definitions"]
        self.assertEqual(len(defz), 1)                     # pages 3-4 fusionnées
        self.assertEqual((defz[0]["start"], defz[0]["end"]), (3, 4))

    def test_zone_signature_stable_and_sensitive(self):
        z = {"label": "definitions", "start": 3, "end": 4, "pages": [3, 4]}
        s1 = CI.zone_signature(PAGES, z)
        s2 = CI.zone_signature(PAGES, z)
        self.assertEqual(s1, s2)                            # stable
        modified = dict(PAGES); modified[3] = PAGES[3] + " NOUVEL AJOUT"
        self.assertNotEqual(s1, CI.zone_signature(modified, z))   # sensible au changement


class TestAssessment(unittest.TestCase):
    KNOWN = ["Beneficiaire", "Capital Garanti", "Franchise"]

    def test_covered_when_all_known(self):
        txt = ("on entend par Beneficiaire la personne designee au contrat ; le Capital Garanti est verse "
               "au terme prevu ; la Franchise applicable est precisee dans les conditions particulieres du present contrat.")
        a = CI.assess_zone(txt, self.KNOWN)
        self.assertIn(a["level"], ("couverte", "partielle"))
        self.assertTrue(a["knowledge_covered"])

    def test_non_couverte_when_novel_only(self):
        txt = "Rente Education et Garantie Obseques sont des dispositifs entierement nouveaux decrits longuement ici pour depasser le seuil."
        a = CI.assess_zone(txt, ["Capital Garanti"])
        self.assertEqual(a["level"], "non_couverte")
        self.assertTrue(a["knowledge_absent"])             # termes nouveaux détectés

    def test_llm_refinement_overrides(self):
        def fake_llm(ztext, det):
            return {"level": "contradictoire", "confidence": 0.9, "suspect": ["montant divergent"]}
        a = CI.assess_zone("Capital Garanti mentionne avec un montant qui semble different du notre ici.",
                           ["Capital Garanti"], llm_fn=fake_llm)
        self.assertEqual(a["level"], "contradictoire")
        self.assertIn("montant divergent", a["knowledge_suspect"])

    def test_llm_absent_keeps_deterministic(self):
        txt = ("Rente Education et Garantie Obseques sont des dispositifs entierement nouveaux, decrits ici "
               "avec suffisamment de details pour depasser le seuil de substance et n'appartiennent pas a la base.")
        a = CI.assess_zone(txt, ["Capital Garanti"], llm_fn=lambda z, d: None)
        self.assertEqual(a["level"], "non_couverte")       # fail-open : déterministe conservé


class TestCoverageMapPersistenceAndResume(unittest.TestCase):
    def test_resume_after_interruption_no_loss(self):
        store, lj, wj = _mem_store()
        cm = CI.CoverageMap("cov.json", load_json=lj, write_json=wj)
        cm.update_zone("doc1", "doc1#definitions:3-4", [3, 4], "non_couverte", 0.55, "h_aaa",
                       "corpus-explorer", ["x"], ["Nouveau"], [], "2026-07-11T10:00:00Z")
        cm.save()                                          # interruption juste après cette zone
        # Nouveau processus : on recharge depuis le store -> rien n'est perdu.
        cm2 = CI.CoverageMap("cov.json", load_json=lj, write_json=wj)
        st = cm2.zone_state("doc1", "doc1#definitions:3-4")
        self.assertIsNotNone(st)
        self.assertEqual(st["level"], "non_couverte")
        self.assertEqual(st["content_hash"], "h_aaa")

    def test_cached_zoning_survives(self):
        store, lj, wj = _mem_store()
        cm = CI.CoverageMap("cov.json", load_json=lj, write_json=wj)
        cm.cache_zoning("doc1", "f_hash1", [{"label": "definitions", "start": 3, "end": 4, "pages": [3, 4]}])
        cm.save()
        cm2 = CI.CoverageMap("cov.json", load_json=lj, write_json=wj)
        self.assertIsNotNone(cm2.cached_zoning("doc1", "f_hash1"))
        self.assertIsNone(cm2.cached_zoning("doc1", "f_hash_DIFFERENT"))   # doc modifié -> cache invalide


class TestSkipAndReprocessing(unittest.TestCase):
    def _cm(self):
        store, lj, wj = _mem_store()
        return CI.CoverageMap("cov.json", load_json=lj, write_json=wj)

    def test_new_zone_needs_exploration(self):
        cm = self._cm()
        self.assertTrue(cm.needs_exploration("doc1", "doc1#garanties:5-5", "h_sig"))

    def test_unchanged_zone_is_skipped(self):
        cm = self._cm()
        cm.update_zone("doc1", "z", [5, 5], "non_couverte", 0.55, "h_sig", "corpus-explorer", [], ["N"], [], "d")
        self.assertFalse(cm.needs_exploration("doc1", "z", "h_sig"))       # même contenu -> jamais retraité

    def test_modified_pdf_triggers_reexploration(self):
        cm = self._cm()
        cm.update_zone("doc1", "z", [5, 5], "couverte", 0.7, "h_old", "corpus-explorer", ["k"], [], [], "d")
        self.assertTrue(cm.needs_exploration("doc1", "z", "h_new"))        # hash changé -> ré-explorer

    def test_covered_zone_excluded_from_ranking(self):
        cm = self._cm()
        z = {"label": "definitions", "start": 3, "end": 4, "pages": [3, 4]}
        cm.update_zone("doc1", CI.zone_key("doc1", z), [3, 4], "couverte", 0.8, "h", "corpus-explorer", ["k"], [], [], "d")
        catalog = [{"doc_id": "doc1", "zone": z}]
        self.assertEqual(CI.rank_targets(cm, catalog, 5), [])             # rien à réexplorer

    def test_never_seen_ranked_before_assessed(self):
        cm = self._cm()
        seen = {"label": "garanties", "start": 5, "end": 5, "pages": [5]}
        cm.update_zone("doc1", CI.zone_key("doc1", seen), [5, 5], "partielle", 0.6, "h", "corpus-explorer", ["k"], ["a"], [], "d")
        never = {"label": "exclusions", "start": 6, "end": 6, "pages": [6]}
        catalog = [{"doc_id": "doc1", "zone": seen}, {"doc_id": "doc1", "zone": never}]
        ranked = CI.rank_targets(cm, catalog, 1)
        self.assertEqual(ranked[0]["zone"]["label"], "exclusions")        # jamais vue d'abord


class TestObsolescence(unittest.TestCase):
    def test_covered_zone_becomes_obsolete_on_change(self):
        store, lj, wj = _mem_store()
        cm = CI.CoverageMap("cov.json", load_json=lj, write_json=wj)
        z = "doc1#garanties:5-5"
        cm.update_zone("doc1", z, [5, 5], "couverte", 0.7, "h_v1", "corpus-explorer", ["Capital"], [], [], "d1")
        # Nouveau contenu (hash différent) ré-évalué 'couverte' -> requalifié 'obsolete' automatiquement.
        st = cm.update_zone("doc1", z, [5, 5], "couverte", 0.7, "h_v2", "corpus-explorer", ["Capital"], [], [], "d2")
        self.assertEqual(st["level"], "obsolete")


class TestTaskGeneration(unittest.TestCase):
    def test_non_couverte_definitions_creates_definition_and_complement(self):
        z = {"label": "definitions", "start": 3, "end": 4, "pages": [3, 4]}
        a = {"level": "non_couverte", "confidence": 0.55, "knowledge_absent": ["Beneficiaire"]}
        tasks = CI.generate_tasks("doc1", z, a, "corpus-explorer")
        types = {t["type"] for t in tasks}
        self.assertIn("definition", types)
        self.assertIn("complement", types)

    def test_rich_types_are_produced(self):
        z = {"label": "garanties", "start": 5, "end": 5, "pages": [5]}
        obsolete = CI.generate_tasks("doc1", z, {"level": "obsolete", "knowledge_absent": []}, "corpus-explorer")
        contra = CI.generate_tasks("doc1", z, {"level": "contradictoire", "knowledge_absent": []}, "corpus-explorer")
        partielle = CI.generate_tasks("doc1", z, {"level": "partielle", "knowledge_absent": []}, "corpus-explorer")
        self.assertIn("mise_a_jour", {t["type"] for t in obsolete})
        self.assertIn("contradiction", {t["type"] for t in contra})
        self.assertIn("comparaison", {t["type"] for t in partielle})     # zone structurante

    def test_task_ids_stable_and_no_duplicates(self):
        z = {"label": "garanties", "start": 5, "end": 5, "pages": [5]}
        a = {"level": "non_couverte", "knowledge_absent": ["Rente"]}
        t1 = CI.generate_tasks("doc1", z, a, "corpus-explorer")
        t2 = CI.generate_tasks("doc1", z, a, "corpus-explorer")
        self.assertEqual([t["task_id"] for t in t1], [t["task_id"] for t in t2])   # ids stables
        # fusion par id (comme le backlog de l'agent) -> aucun doublon
        merged = {t["task_id"]: t for t in (t1 + t2)}
        self.assertEqual(len(merged), len(t1))


class TestProgressiveCoverage(unittest.TestCase):
    def test_ratio_increases_as_zones_get_covered(self):
        store, lj, wj = _mem_store()
        cm = CI.CoverageMap("cov.json", load_json=lj, write_json=wj)
        z1, z2 = "doc1#a:1-1", "doc1#b:2-2"
        cm.update_zone("doc1", z1, [1, 1], "non_couverte", 0.5, "h1", "cx", [], ["N"], [], "d")
        cm.update_zone("doc1", z2, [2, 2], "non_couverte", 0.5, "h2", "cx", [], ["N"], [], "d")
        r0 = cm.global_ratio()
        cm.update_zone("doc1", z1, [1, 1], "couverte", 0.8, "h1b", "cx", ["k"], [], [], "d")
        r1 = cm.global_ratio()
        cm.update_zone("doc1", z2, [2, 2], "couverte", 0.8, "h2b", "cx", ["k"], [], [], "d")
        r2 = cm.global_ratio()
        self.assertLess(r0, r1)
        self.assertLess(r1, r2)
        self.assertEqual(r2, 1.0)                          # tend vers 100 %


class TestExecutableEnqueueDedup(unittest.TestCase):
    """Les tâches exécutables enfilées dans la file de l'orchestrateur ne créent jamais de doublon
    (empreinte contract+category partagée avec _build_llm_tasks ; reruns idempotents)."""
    def test_same_zone_enqueued_twice_is_single_task(self):
        import tempfile, orch
        tmp = tempfile.mkdtemp()
        q = orch.TaskQueue(tmp)
        fields = dict(priority=4, contract="Avizen", category="garanties",
                      estimated_input_tokens=2500, estimated_output_tokens=700,
                      source_gap_id="corpus_explorer:doc1#garanties:5-5", human_validation_required=True)
        _t1, new1 = q.add("extraction-llm", **fields)
        _t2, new2 = q.add("extraction-llm", **fields)     # même (contract, category) -> même empreinte
        self.assertTrue(new1)
        self.assertFalse(new2)                            # aucun doublon
        self.assertEqual(len(q.data["tasks"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
