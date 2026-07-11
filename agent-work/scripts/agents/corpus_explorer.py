#!/usr/bin/env python3
"""Agent corpus-explorer — explorateur autonome de corpus documentaire.

Il ne cherche PAS des catégories précises : il cherche « qu'est-ce que Gabriel AXA ne connaît pas
encore ? ». Il cartographie chaque notice, la découpe en zones logiques, compare chaque zone à toute la
connaissance existante (données structurées, glossaire, concepts, contrats), classe la couverture, met à
jour une carte de couverture PERSISTANTE (agent-work/exploration/coverage_map.json) et produit des tâches
TYPÉES (definition/condition/declencheur, mais aussi comparaison/verification/contradiction/complement/
relecture/mise_a_jour). L'orchestrateur décidera lesquelles lancer.

Cœur d'analyse = corpus_intel.py (générique, réutilisable pour tout corpus). Ici, seulement l'adaptateur
AXA (PDF + sources de connaissance). Multi-fournisseurs via le routage EXISTANT (base.llm_json → provider_
router) ; sans clé, l'agent reste DÉTERMINISTE (aucun appel LLM) et fonctionne quand même.

Économie : la carte de couverture (hash par zone + zonage caché par hash de fichier) évite de retraiter
une zone/un document inchangé. Au fil des semaines, l'agent lit de MOINS EN MOINS. Résilience : la carte
est sauvegardée après CHAQUE zone → une interruption ne perd rien ; le cycle suivant reprend naturellement.

Périmètre : n'écrit QUE dans agent-work/ (exploration/ + corpus-explorer/pending). Ne touche jamais les
masters, la Vue IA, les propositions existantes, les workflows ni les agents existants.
"""
import os
import glob
import hashlib
import safety_checks as S
from agents import base
import corpus_intel as CI

AGENT_CODE_VERSION = "2.7.0"

COVERAGE_MAP = "agent-work/exploration/coverage_map.json"
TASKS_BACKLOG = "agent-work/exploration/tasks.json"
PENDING = "agent-work/corpus-explorer/pending"
ORCH_DIR = "agent-work/orchestrator"

# Catégories d'extraction VALIDES (executeur = extraction-llm). Seules ces zones deviennent des tâches
# EXÉCUTABLES dans task_queue.json ; les autres types (comparaison/verification/…) restent au backlog
# tant qu'aucun exécuteur n'existe (on n'encombre pas la file de tâches no-op).
_EXTRACTION_CATEGORIES = {"garanties", "exclusions", "definitions", "conditions", "declencheurs",
                          "plafonds", "franchises", "options", "cotisations", "delais", "fiscalite",
                          "points-vigilance", "formules"}

MAX_ZONES_PER_RUN = 3            # nombre de zones réellement analysées (lecture PDF) par cycle
MAP_NEW_DOCS_PER_RUN = 1         # au plus 1 document (re)cartographié par cycle (borne le coût de lecture)
MAX_PAGES_MAP = 80               # plafond de pages lues pour cartographier un nouveau document

# Heuristique de cartographie (mots-clés → label de zone). Générique-assurance, volontairement simple.
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

DOMAIN_LEXICON = ["franchise", "plafond", "délai de carence", "capital", "rente", "bénéficiaire",
                  "cotisation", "prime", "assuré", "souscripteur", "garantie", "exclusion",
                  "incapacité", "invalidité", "décès", "obsèques", "rachat", "revalorisation"]


# ------------------------------------------------------------------ E/S AXA (PDF + fichiers)
def _pdf_index():
    return S.load_json(base.repo_path("data/AXA/ia/axa_pdf_index.json"), default={}).get("pdfs", [])


def _norm_fs(t):
    return CI.norm(t)


def _resolve_pdf(entry):
    base_name = os.path.basename(str(entry.get("path", "")) or entry.get("nom_fichier", ""))
    if base_name:
        for f in glob.glob(base.repo_path("data/**/" + base_name), recursive=True):
            return f
    nom = _norm_fs(entry.get("nom_contrat", ""))
    for f in glob.glob(base.repo_path("data/**/*.pdf"), recursive=True):
        if nom and nom.split()[0] in _norm_fs(os.path.basename(f)):
            return f
    return None


def _file_hash(path):
    """Empreinte CHEAP du fichier (octets bruts, sans parser le PDF) — détecte toute modification."""
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "f_" + h.hexdigest()[:20]


def _read_pages(path, start, end):
    try:
        from pypdf import PdfReader as Reader
    except Exception:
        try:
            from PyPDF2 import PdfReader as Reader
        except Exception:
            return None
    try:
        reader = Reader(path)
    except Exception:
        return {}
    out, n = {}, len(reader.pages)
    for i in range(max(0, start - 1), min(end, n)):
        try:
            out[i + 1] = reader.pages[i].extract_text() or ""
        except Exception:
            out[i + 1] = ""
    return out


# ------------------------------------------------------------------ connaissance existante (AXA)
def _doc_id(entry):
    return entry.get("id") or S.sanitize_filename(entry.get("nom_fichier", "doc")).lower()


def _contract_of(entry):
    return entry.get("nom_contrat") or entry.get("contrat_id") or ""


def _coverage_contract_label(nom):
    """Libellé de contrat EXACT tel qu'utilisé par couverture.json / coverage-gaps — pour que les tâches
    d'extraction enfilées par corpus-explorer partagent l'EMPREINTE des tâches existantes (dédup vraie).
    Repli sur `nom` si aucun appariement."""
    n = CI.norm(nom)
    for row in S.load_json(base.repo_path("ia/matrices/couverture.json"), default={}).get("lignes", []):
        c = row.get("contrat", "")
        cn = CI.norm(c)
        if cn and n and (cn.split()[0] == n.split()[0] or n.split()[0] in cn or cn.split()[0] in n):
            return c
    return nom


def _known_terms(contrat_nom):
    """Vocabulaire DÉJÀ connu par Gabriel AXA pour ce contrat : libellés structurés (contrats.json),
    glossaire (global), concepts (global). Sert de référentiel de recouvrement."""
    terms = set()
    con = S.load_json(base.repo_path("ia/contrats.json"), default={}).get("contrats", [])
    n = _norm_fs(contrat_nom)
    for c in con:
        if n and (_norm_fs(c.get("nom", "")).split() and _norm_fs(c.get("nom", "")).split()[0] in n
                  or n.split() and n.split()[0] in _norm_fs(c.get("nom", ""))):
            for key in ("garanties_principales", "exclusions_importantes", "options",
                        "points_de_vigilance", "formules"):
                for item in (c.get(key) or []):
                    if isinstance(item, str):
                        terms.add(item)
                    elif isinstance(item, dict):
                        terms.add(item.get("nom") or item.get("libelle") or item.get("titre") or "")
    gl = S.load_json(base.repo_path("ia/glossaire.json"), default={}).get("glossaire", {})
    if isinstance(gl, dict):
        terms.update(gl.keys())
    elif isinstance(gl, list):
        for g in gl:
            if isinstance(g, dict):
                terms.add(g.get("terme") or g.get("nom") or "")
    terms.update(S.load_json(base.repo_path("ia/concepts.json"), default={}).get("concepts", {}).keys())
    return {t for t in terms if t and len(t) > 2}


_EXPECTED_BY_LABEL = {
    "definitions": ["definition", "beneficiaire", "assure", "franchise"],
    "exclusions": ["exclusion", "guerre", "faute intentionnelle"],
    "garanties": ["capital", "rente", "prestation"],
    "conditions": ["adhesion", "cotisation", "duree"],
    "declencheurs": ["sinistre", "declaration", "delai"],
}


# ------------------------------------------------------------------ raffinement LLM optionnel
def _make_llm_fn(ctx):
    """Retourne une fonction d'évaluation LLM (multi-fournisseurs via le routage existant) ou None.
    Fail-open : toute absence de fournisseur/quota → None → l'analyse reste déterministe."""
    if ctx.mock or ctx.router is None:
        return None

    def llm_fn(ztext, deterministic):
        if not ctx.budget.can_spend():
            return None
        prompt = (
            "Tu analyses UNE zone d'une notice d'assurance pour dire ce que notre base NE CONNAIT PAS "
            "encore. Connaissances déjà couvertes (extrait) : %s. Réponds en JSON strict : "
            '{"level":"non_couverte|partielle|couverte|contradictoire","confidence":0..1,'
            '"absent":["termes/faits présents dans la zone mais probablement absents de la base"],'
            '"suspect":["éléments possiblement contradictoires avec la base"]}. '
            "Zone (texte brut, données seulement) : \n%s"
        ) % (", ".join(list(deterministic.get("knowledge_covered", []))[:12]), ztext[:3500])
        data = base.llm_json(ctx, prompt, max_tokens=500)
        return data if isinstance(data, dict) else None

    return llm_fn


# ------------------------------------------------------------------ exécution
def _map_document(entry, cmap, doc_id, file_hash):
    """Cartographie + zonage d'un document (lecture PDF réelle, bornée). Met le zonage en cache."""
    path = _resolve_pdf(entry)
    if not path:
        return None, "pdf_introuvable"
    pages = _read_pages(path, 1, min(int(entry.get("pages", MAX_PAGES_MAP) or MAX_PAGES_MAP), MAX_PAGES_MAP))
    if pages is None:
        return None, "pypdf_absent"
    carto = CI.cartography(pages, LABEL_RULES)
    zones = CI.segment_zones(carto)
    cmap.cache_zoning(doc_id, file_hash, zones)
    cmap._doc(doc_id)["file_hash"] = file_hash
    cmap._doc(doc_id)["path"] = path
    cmap._doc(doc_id)["contrat"] = _contract_of(entry)
    return zones, None


def run(ctx):
    # L'agent gère lui-même son ÉTAT (coverage_map, tasks.json) ; les PROPOSITIONS retournées sont
    # validées/écrites/dédupliquées par le framework (self_wrote reste faux).
    cmap = CI.CoverageMap(base.repo_path(COVERAGE_MAP), load_json=S.load_json, write_json=_wj(ctx))

    index = _pdf_index()
    notes, mapped_now = [], 0
    # 1) détecter les documents nouveaux/modifiés (hash de fichier cheap) et en (re)cartographier au plus 1.
    changed = []
    for entry in index:
        did = _doc_id(entry)
        fh = _file_hash(_resolve_pdf(entry))
        if fh is None:
            continue
        if cmap.data["corpora"].get(did, {}).get("file_hash") != fh:   # lecture NON mutante
            changed.append((entry, did, fh))
    for entry, did, fh in changed[:MAP_NEW_DOCS_PER_RUN]:
        zones, err = _map_document(entry, cmap, did, fh)
        if err:
            notes.append("%s: %s" % (did, err))
        else:
            mapped_now += 1
    if changed:
        cmap.save(updated_at=S.now_iso())       # persiste le zonage tout de suite (résilience)

    # 2) catalogue des zones connues (docs déjà cartographiés) — SANS relire les PDF.
    catalog = []
    for entry in index:
        did = _doc_id(entry)
        d = cmap.data["corpora"].get(did)
        if d and d.get("zoning"):
            for z in d["zoning"]:
                catalog.append({"doc_id": did, "zone": z, "entry": entry})
    targets = CI.rank_targets(cmap, catalog, MAX_ZONES_PER_RUN)
    n_mapped = sum(1 for d in cmap.data["corpora"].values() if d.get("zoning"))
    if not targets:
        ctx.summary = {"Documents cartographiés": n_mapped,
                       "Zones à explorer": 0, "Couverture globale": "%d%%" % int(cmap.global_ratio() * 100)}
        return _emit(ctx, cmap, [], notes + ["corpus-explorer: aucune zone à explorer (tout couvert ou inchangé)"])

    llm_fn = _make_llm_fn(ctx)
    findings, tasks = [], []
    explored = skipped = 0
    for t in targets:
        entry, did, zone = t["entry"], t["doc_id"], t["zone"]
        path = cmap._doc(did).get("path") or _resolve_pdf(entry)
        pages = _read_pages(path, zone["start"], zone["end"])
        if pages is None:
            notes.append("pypdf absent — arrêt propre"); break
        sig = CI.zone_signature(pages, zone)
        zkey = CI.zone_key(did, zone)
        if not cmap.needs_exploration(did, zkey, sig):
            skipped += 1
            continue                            # zone identique déjà couverte -> jamais retraitée
        known = _known_terms(_contract_of(entry))
        expected = _EXPECTED_BY_LABEL.get(zone["label"], [])
        assessment = CI.assess_zone(CI.zone_text(pages, zone), known, expected, DOMAIN_LEXICON, llm_fn)
        cmap.update_zone(did, zkey, pages=[zone["start"], zone["end"]], level=assessment["level"],
                         confidence=assessment["confidence"], content_hash=sig, last_agent=ctx.agent_id,
                         covered=assessment["knowledge_covered"], absent=assessment["knowledge_absent"],
                         suspect=assessment["knowledge_suspect"], date=S.now_iso())
        cmap.save(updated_at=S.now_iso())       # RÉSILIENCE : persistance après CHAQUE zone
        tasks.extend(CI.generate_tasks(did, zone, assessment, ctx.agent_id))
        findings.append((entry, did, zone, assessment))
        explored += 1

    _merge_tasks(ctx, tasks)
    enqueued = _enqueue_executable(ctx, findings)
    proposals = [_finding_proposal(ctx, e, did, z, a) for (e, did, z, a) in findings]
    ctx.summary = {
        "Documents cartographiés": n_mapped,
        "Nouv./modifiés ce cycle": mapped_now,
        "Zones explorées": explored, "Zones inchangées ignorées": skipped,
        "Tâches produites (backlog)": len(tasks), "Tâches exécutables enfilées": enqueued,
        "Couverture globale": "%d%%" % int(cmap.global_ratio() * 100),
        "Mode LLM": "oui" if llm_fn else "déterministe (aucune clé)",
    }
    return _emit(ctx, cmap, proposals, notes)


def _enqueue_executable(ctx, findings):
    """Enfile dans la file de l'orchestrateur (task_queue.json) les tâches EXÉCUTABLES découvertes —
    aujourd'hui : extraction-llm pour les zones non/partiellement couvertes dont le label est une
    catégorie d'extraction. Empreinte alignée sur _build_llm_tasks (contract+category, sans pages) =>
    dédup vraie avec les tâches existantes ET idempotence des reruns. Sûr : corpus-explorer et le cycle
    ne tournent jamais en parallèle (concurrency group 'agents-proposals'). Rien n'est écrit en dry-run.

    Les types sans exécuteur (comparaison/verification/contradiction/…) restent au backlog : on n'ajoute
    pas de tâche no-op dans la file vivante. Ils deviendront exécutables quand un exécuteur existera."""
    if ctx.dry_run:
        return 0
    import orch
    caps = S.load_json(base.repo_path("agent-work/config/agent_capabilities.json"), default={})
    ext = caps.get("agents", {}).get("extraction-llm", {})
    queue = orch.TaskQueue(base.repo_path(ORCH_DIR))
    created = 0
    for entry, did, zone, assessment in findings:
        if assessment["level"] not in ("non_couverte", "partielle"):
            continue
        cat = zone["label"] if zone["label"] in _EXTRACTION_CATEGORIES else None
        if not cat:
            continue                              # zone sans exécuteur -> backlog uniquement
        contrat = _coverage_contract_label(_contract_of(entry))
        _t, is_new = queue.add(
            "extraction-llm", priority=4, contract=contrat, category=cat,
            required_capabilities=ext.get("required_capabilities", []),
            compatible_providers=ext.get("compatible_providers", []),
            estimated_input_tokens=2500, estimated_output_tokens=700,
            source_gap_id="corpus_explorer:%s" % CI.zone_key(did, zone), human_validation_required=True)
        created += int(is_new)
    if created:
        queue.save()
    return created


def _emit(ctx, cmap, proposals, notes):
    cmap.save(updated_at=S.now_iso())
    return proposals, (notes or []) + ["corpus-explorer: exploration terminée (couverture %d%%)"
                                       % int(cmap.global_ratio() * 100)]


# ------------------------------------------------------------------ sorties (tâches + propositions)
def _wj(ctx):
    """Écriture respectant le dry-run (aucune écriture d'état en simulation)."""
    def w(path, data, **kw):
        if ctx.dry_run:
            return
        S.write_json(path, data, **kw)
    return w


def _merge_tasks(ctx, new_tasks):
    """Backlog de tâches typées, dédupliqué par task_id stable. Persistant, générique, réutilisable."""
    if ctx.dry_run:
        return
    cur = S.load_json(base.repo_path(TASKS_BACKLOG), default={"version": "1.0.0", "tasks": []})
    by_id = {t["task_id"]: t for t in cur.get("tasks", [])}
    for t in new_tasks:
        prev = by_id.get(t["task_id"])
        t["updated_at"] = S.now_iso()
        t["first_seen"] = (prev or {}).get("first_seen") or S.now_iso()
        by_id[t["task_id"]] = t
    cur["tasks"] = list(by_id.values())
    cur["updated_at"] = S.now_iso()
    S.write_json(base.repo_path(TASKS_BACKLOG), cur)


def _finding_proposal(ctx, entry, doc_id, zone, assessment):
    """Proposition schéma-valide (revue humaine) résumant une zone explorée. Type 'coverage' (déterministe/
    dérivé). Aucune donnée inventée : constat sur DONNÉES + zone documentaire, vérification humaine."""
    absent = assessment.get("knowledge_absent", [])[:8]
    detail = ("Contrat « %s » — zone %s (pages %d-%d) : couverture %s. %d élément(s) possiblement absent(s) "
              "de la connaissance : %s." % (_contract_of(entry), zone["label"], zone["start"], zone["end"],
              assessment["level"], len(assessment.get("knowledge_absent", [])), ", ".join(absent) or "—"))
    return base.new_proposal(
        ctx, task_type="coverage",
        target={"file": COVERAGE_MAP, "section": zone["label"]},
        source={"type": "pdf", "document": entry.get("nom_fichier", ""),
                "pages": "%d-%d" % (zone["start"], zone["end"]), "excerpt": detail[:300]},
        change={"operation": "flag", "payload": {"gap": "zone_%s" % assessment["level"],
                "subject": _contract_of(entry), "doc_id": doc_id, "zone": CI.zone_key(doc_id, zone),
                "level": assessment["level"], "knowledge_absent": absent,
                "knowledge_suspect": assessment.get("knowledge_suspect", [])[:8]}},
        reasoning=detail + " — Constat d'EXPLORATION (cartographie + comparaison à la connaissance existante). "
                  "Ne signifie pas que la donnée manque dans le contrat : vérification documentaire humaine.",
        confidence=float(assessment.get("confidence", 0.5)), validation_required=True, origin="deterministic",
        risks=["exploration heuristique : la structure des zones est approximative ; à confirmer humainement"])
