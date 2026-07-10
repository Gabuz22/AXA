#!/usr/bin/env python3
"""Agent Qualité documentaire — DÉTERMINISTE (aucun appel LLM).

Vérifie couverture, synchronisation des sorties /ia, liens internes, notices PDF, IDs, versions,
pages IA, matrices, tests de routage. Ne corrige jamais l'application : il écrit un rapport dans
quality/reports/ et des incidents dans quality/incidents/. Reste read-only sur le produit :
s'il régénère /ia pour lire les métriques, il restaure ensuite l'arbre (git checkout -- ia).
"""
import os, re, glob, json, subprocess
import safety_checks as S
from agents import base

EXPECTED_IA_PAGES = ["index", "instructions-maitres", "guide-ia", "manifeste", "outils", "routage",
                     "pertinence", "qualite-routage", "concepts", "comparateur", "matrices",
                     "sources-officielles", "contrats", "glossaire", "notices"]


def _check(name, ok, detail, severity="warn"):
    return {"name": name, "ok": bool(ok), "detail": detail, "severity": severity}


def _run(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, cwd=S.REPO_ROOT, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout or "", r.stderr or ""
    except Exception as e:
        return 1, "", str(e)


def _version_consistency():
    checks = []
    vj = S.load_json(base.repo_path("version.json"), default={}).get("version")
    build = base.read_text("scripts/build_ia.py") or ""
    m = re.search(r'VERSION\s*=\s*"([^"]+)"', build)
    bv = m.group(1) if m else None
    checks.append(_check("version.json présent", bool(vj), "version.json=%s" % vj, "high"))
    checks.append(_check("build_ia VERSION lisible", bool(bv), "build_ia VERSION=%s" % bv, "warn"))
    idx = base.read_text("ia/index.html") or ""
    footer_match = re.search(r"Vue IA v([0-9.]+)", idx)
    fv = footer_match.group(1) if footer_match else None
    checks.append(_check("cohérence version build_ia vs footer /ia", bv == fv,
                         "build=%s footer=%s" % (bv, fv), "high"))
    return checks


def _ia_regen_sync():
    """Régénère /ia, lit les métriques, vérifie que rien n'a changé, puis restaure /ia."""
    rc, out, err = _run(["python", "scripts/build_ia.py"])
    checks = []
    cov = re.search(r"Couverture données\s*:\s*([0-9]+%|partielle)", out)
    routage = re.search(r"contrats P=([0-9]+)%.*?statut ([0-9]+)%.*?faux positifs contrats\s*:\s*([0-9]+)", out)
    checks.append(_check("générateur /ia s'exécute", rc == 0, (err or out)[-300:] if rc else "ok", "high"))
    if cov:
        checks.append(_check("couverture données = 100%", cov.group(1) == "100%", "couverture=%s" % cov.group(1), "high"))
    if routage:
        fp = int(routage.group(3))
        checks.append(_check("routage sans faux positif contrat", fp == 0, "faux_positifs=%s statut=%s%%" % (fp, routage.group(2)), "high"))
    # /ia doit rester synchronisé avec les données (diff vide après régénération)
    rc2, diffout, _ = _run(["git", "diff", "--name-only", "--", "ia"])
    changed = [l for l in diffout.splitlines() if l.strip()]
    checks.append(_check("sorties /ia publiées synchronisées", len(changed) == 0,
                         "fichiers /ia désynchronisés: %d" % len(changed), "high"))
    # Restaurer /ia (ne jamais modifier les sorties publiées)
    _run(["git", "checkout", "--", "ia"])
    return checks, {"coverage": cov.group(1) if cov else None,
                    "routage_faux_positifs": int(routage.group(3)) if routage else None}


def _dead_internal_links(sample=40):
    files = sorted(glob.glob(base.repo_path("ia/*.html")))[:sample]
    broken = []
    for f in files:
        try:
            html = open(f, "r", encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for href in re.findall(r'href="([^"#?]+\.html)"', html):
            if href.startswith("http") or href.startswith("//") or ".." in href:
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(f), href))
            if not os.path.isfile(target):
                broken.append("%s -> %s" % (os.path.basename(f), href))
    return [_check("liens internes /ia valides", len(broken) == 0, "cassés: %d %s" % (len(broken), broken[:5]), "high")]


def _pdf_notices():
    idx = S.load_json(base.repo_path("data/AXA/ia/axa_pdf_index.json"), default={})
    pdfs = idx.get("pdfs", []) if isinstance(idx, dict) else (idx or [])
    resolved = sum(1 for p in pdfs if os.path.isfile(base.repo_path(str(p.get("path", "")))))
    total = len(pdfs)
    return [_check("notices PDF résolues sur disque", resolved == total,
                   "%d/%d notices résolues" % (resolved, total), "warn")], {"pdfs_resolved": resolved, "pdfs_total": total}


def _ids_unique():
    c = S.load_json(base.repo_path("ia/contrats.json"), default={})
    contrats = c.get("contrats", []) if isinstance(c, dict) else []
    ids = [x.get("id") for x in contrats]
    missing = sum(1 for i in ids if not i)
    dup = len(ids) - len(set(i for i in ids if i))
    return [_check("IDs contrats présents et uniques", missing == 0 and dup == 0,
                   "manquants=%d doublons=%d sur %d" % (missing, dup, len(ids)), "high")]


def _ia_pages_present():
    missing = [p for p in EXPECTED_IA_PAGES if not os.path.isfile(base.repo_path("ia/%s.html" % p))]
    return [_check("pages IA attendues présentes", not missing, "manquantes: %s" % missing, "high")]


def _matrices_parse():
    bad = []
    for f in glob.glob(base.repo_path("ia/matrices/*.json")):
        try:
            json.load(open(f, "r", encoding="utf-8"))
        except Exception as e:
            bad.append("%s (%s)" % (os.path.basename(f), e))
    return [_check("matrices JSON parseables", not bad, "invalides: %s" % bad, "warn")]


def run(ctx):
    ctx.self_wrote = True
    checks = []
    checks += _version_consistency()
    sync_checks, sync_metrics = _ia_regen_sync()
    checks += sync_checks
    checks += _dead_internal_links()
    pdf_checks, pdf_metrics = _pdf_notices()
    checks += pdf_checks
    checks += _ids_unique()
    checks += _ia_pages_present()
    checks += _matrices_parse()

    failures = [c for c in checks if not c["ok"]]
    report = {
        "run_id": ctx.run_id, "agent_id": ctx.agent_id, "generated_at": S.now_iso(),
        "summary": {"total": len(checks), "passed": len(checks) - len(failures), "failed": len(failures)},
        "metrics": {**sync_metrics, **pdf_metrics},
        "checks": checks,
    }
    reports_dir = base.repo_path("agent-work/quality/reports")
    S.write_json(os.path.join(reports_dir, "quality_%s.json" % S.stamp()), report)

    # Un incident = une proposition schéma-valide (type quality, operation report) => ingérable par le coordinateur.
    proposals = []
    incidents_dir = base.repo_path("agent-work/quality/incidents")
    for c in failures:
        p = base.new_proposal(
            ctx, task_type="quality",
            target={"file": "ia/", "section": c["name"]},
            source={"type": "repo", "document": "scripts/build_ia.py + ia/", "excerpt": c["detail"][:400]},
            change={"operation": "report", "payload": {"check": c["name"], "detail": c["detail"], "severity": c["severity"]}},
            reasoning="Contrôle qualité déterministe en échec : %s — %s" % (c["name"], c["detail"]),
            confidence=0.99, validation_required=True, origin="deterministic",
            risks=["signal de qualité ; aucune correction appliquée automatiquement"],
        )
        proposals.append(p)
        if not ctx.dry_run:
            S.write_json(os.path.join(incidents_dir, p["proposal_id"] + ".json"), p)

    notes = ["qualité: %d/%d contrôles OK" % (report["summary"]["passed"], report["summary"]["total"])]
    if ctx.dry_run:
        notes.append("dry-run: incidents non persistés (rapport écrit dans quality/reports)")
    return proposals, notes
