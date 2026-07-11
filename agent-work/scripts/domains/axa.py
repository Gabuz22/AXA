#!/usr/bin/env python3
"""Adaptateur du domaine AXA (assurance) — premier domaine de la plateforme.

Ne fait que DÉCRIRE ce que le domaine AXA contient (documents, connaissance structurée déjà sourcée,
vocabulaire, environnement réglementaire). Le moteur générique (graphe, couverture, ingestion) s'en sert
sans rien savoir d'AXA. Réutilise les fichiers existants (contrats.json, glossaire, concepts, index PDF,
sources officielles) en LECTURE seule — ne modifie jamais le produit.
"""
import safety_checks as S
from agents import base
from domain_adapter import DomainAdapter

# Chaque clé structurée de contrats.json -> un sous-type d'entité L2.
_STRUCTURED = {
    "garanties_principales": "garantie",
    "exclusions_importantes": "exclusion",
    "options": "option",
    "points_de_vigilance": "point_vigilance",
    "formules": "formule",
}

LABEL_RULES = [
    ("sommaire", ["sommaire", "table des matieres"]),
    ("definitions", ["definition", "on entend par", "au sens du present", "glossaire", "lexique"]),
    ("garanties", ["garantie", "nous garantissons", "prestation", "capital garanti", "rente", "versement"]),
    ("exclusions", ["exclusion", "sont exclus", "ne sont pas garantis", "nous ne garantissons pas", "ne couvre pas"]),
    ("conditions", ["condition", "adhesion", "souscription", "prise d'effet", "cotisation", "duree du contrat"]),
    ("declencheurs", ["en cas de", "sinistre", "declaration", "survenance", "fait generateur", "mise en jeu"]),
    ("resiliation", ["resiliation", "renonciation", "denonciation", "cessation"]),
    ("fiscalite", ["fiscal", "fiscalite", "impot", "prelevement"]),
    ("titre", ["notice d'information", "conditions generales", "contrat"]),
]


def _contrats():
    return S.load_json(base.repo_path("ia/contrats.json"), default={}).get("contrats", [])


def CI_norm(t):
    import corpus_intel as CI
    return CI.norm(t)


def _concept_keywords(key, c):
    """Mots-clés d'appariement d'un concept réglementaire (pour relier les entités de contrat concernées)."""
    kws = {CI_norm(key)}
    kws.add(CI_norm(c.get("nom") or ""))
    for w in CI_norm(c.get("nom") or "").split():
        if len(w) > 3:
            kws.add(w)
    return sorted(k for k in kws if k)


class AXAAdapter(DomainAdapter):
    domain_id = "axa-contrat"
    environment_domains = ("fiscalite", "reglementation", "droit", "securite-sociale")

    # -------------------------------------------------------------- documents
    def documents(self):
        out = []
        for e in S.load_json(base.repo_path("data/AXA/ia/axa_pdf_index.json"), default={}).get("pdfs", []):
            out.append({"doc_id": e.get("id"), "subject": e.get("nom_contrat"),
                        "document": e.get("nom_fichier"), "pages": e.get("pages")})
        return out

    # -------------------------------------------------------------- connaissance déjà structurée (amorce L2 + L1)
    def structured_entities(self):
        out = []
        for c in _contrats():
            subject = c.get("nom")
            for key, subtype in _STRUCTURED.items():
                for item in (c.get(key) or []):
                    if not isinstance(item, dict):
                        # tolère une valeur simple (autre domaine réutilisant l'adaptateur)
                        item = {"titre": str(item)}
                    label = item.get("titre") or item.get("nom") or ""
                    if not label:
                        continue
                    src = item.get("source") or {}
                    conf = item.get("confiance") or {}
                    score = conf.get("score") if isinstance(conf, dict) else None
                    out.append({
                        "subject": subject, "subtype": subtype, "label": label,
                        "content": {"resume": item.get("resume_humain") or item.get("resume"),
                                    "section": src.get("section"),
                                    "impact_client": item.get("impact_client"),
                                    "keywords": [str(k) for k in (item.get("mots_cles") or [])][:30]},
                        "source": {"document": src.get("document_source"), "page": src.get("page"),
                                   "section": src.get("section")} if src.get("document_source") else None,
                        "confidence": round((score / 100.0), 3) if isinstance(score, (int, float)) else 0.6,
                    })
        return out

    # -------------------------------------------------------------- vocabulaire connu
    def known_terms(self, subject):
        terms = set()
        n = S.sanitize_filename(subject or "").lower()
        for c in _contrats():
            if n and S.sanitize_filename(c.get("nom", "")).lower().split("_")[0] in n:
                for key in _STRUCTURED:
                    for item in (c.get(key) or []):
                        t = item.get("titre") if isinstance(item, dict) else str(item)
                        if t:
                            terms.add(t)
        gl = S.load_json(base.repo_path("ia/glossaire.json"), default={}).get("glossaire", {})
        if isinstance(gl, dict):
            terms.update(gl.keys())
        terms.update(S.load_json(base.repo_path("ia/concepts.json"), default={}).get("concepts", {}).keys())
        return {t for t in terms if t and len(t) > 2}

    def label_rules(self):
        return LABEL_RULES

    # -------------------------------------------------------------- environnement (couche séparée)
    def _fiscal(self, domaines):
        return "fiscalite" if any("fiscal" in CI_norm(d) for d in (domaines or [])) else "reglementation"

    def official_sources(self):
        env = self.environment_sources()
        return [{"id": a["id"], "autorite": a["nom"], "url": a.get("url"), "theme": None}
                for a in env["authorities"]]

    def environment_sources(self):
        """Référentiel d'ENVIRONNEMENT (NAVIGATION vers autorités publiques, AUCUN contenu réglementaire).
        Retourne {authorities:[...], concepts:[...]} normalisé. Domaines séparés (fiscalite/reglementation).
        `as_of` = date de génération du référentiel (fraîcheur)."""
        data = S.load_json(base.repo_path("ia/sources-officielles.json"), default={})
        as_of = (data.get("meta") or {}).get("genere_le")
        authorities = []
        for key, a in (data.get("autorites") or {}).items():
            authorities.append({"id": key, "nom": a.get("nom") or key, "url": a.get("url"),
                                "type": a.get("type"), "role": a.get("role"), "as_of": as_of})
        concepts = []
        for key, c in (data.get("concepts") or {}).items():
            if not c.get("matiere_evolutive"):
                continue                              # on n'ancre que les matières ÉVOLUTIVES (droit/fiscal)
            concepts.append({"key": key, "nom": c.get("nom") or key,
                             "domain": self._fiscal(c.get("domaines")),
                             "authorities": [x.get("cle") for x in (c.get("autorites") or []) if x.get("cle")],
                             "keywords": _concept_keywords(key, c), "as_of": as_of})
        return {"authorities": authorities, "concepts": concepts}

    # -------------------------------------------------------------- résolution slug<->nom
    def subject_of(self, ref):
        if not ref:
            return ref
        rn = S.sanitize_filename(str(ref)).lower()
        for c in _contrats():
            nom = c.get("nom", "")
            if S.sanitize_filename(nom).lower() == rn or S.sanitize_filename(nom).lower().split("_")[0] == rn.split("_")[0]:
                return nom
        return ref
