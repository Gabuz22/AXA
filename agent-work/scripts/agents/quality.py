#!/usr/bin/env python3
"""Agent Qualité documentaire — DÉTERMINISTE (aucun appel LLM, aucune API).

Parcourt réellement le dépôt et contrôle : JSON valides, ai-manifest, sitemap, cohérence de version,
synchronisation des sorties /ia, liens internes, pages IA, notices/PDF, IDs stables et doublons,
cohérence contrats↔pages↔matrices↔graphe, couverture, tests de routage, fichiers orphelins, pages
sans source, sources sans page/notice. Il **ne corrige rien** : il produit un rapport JSON complet,
un rapport Markdown court, des incidents structurés, et un résumé lisible pour GitHub Actions.
Il compare au rapport précédent pour distinguer anomalie **nouvelle / connue / corrigée**.
"""
import os, re, glob, json, subprocess
import safety_checks as S
from agents import base

EXPECTED_IA_PAGES = ["index", "instructions-maitres", "guide-ia", "manifeste", "outils", "routage",
                     "pertinence", "qualite-routage", "concepts", "comparateur", "matrices",
                     "sources-officielles", "contrats", "glossaire", "notices"]
CATEGORY_PAGES = ["garanties", "exclusions", "definitions", "conditions", "declencheurs", "plafonds", "franchises"]


def _check(name, ok, detail, severity="warn"):
    return {"name": name, "ok": bool(ok), "detail": str(detail)[:400], "severity": severity}


def _run(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, cwd=S.REPO_ROOT, capture_output=True, timeout=timeout)
        return (r.returncode, (r.stdout or b"").decode("utf-8", "replace"),
                (r.stderr or b"").decode("utf-8", "replace"))
    except Exception as e:
        return 1, "", str(e)


def _all_json_paths():
    paths = []
    for pat in ("ia/*.json", "ia/matrices/*.json", "data/AXA/ia/*.json",
                "agent-work/config/*.json", "agent-work/schemas/*.json"):
        paths += glob.glob(base.repo_path(pat))
    return paths


def _json_valid():
    bad = []
    for p in _all_json_paths():
        try:
            json.load(open(p, "r", encoding="utf-8"))
        except Exception as e:
            bad.append("%s (%s)" % (os.path.relpath(p, S.REPO_ROOT), e))
    return _check("tous les JSON valides", not bad, "invalides: %s" % bad[:5], "high"), len(_all_json_paths())


def _manifest_sitemap():
    checks = []
    man = S.load_json(base.repo_path("ia/ai-manifest.json"), default={})
    checks.append(_check("ai-manifest.json cohérent", bool(man.get("entry_point")) and bool(man.get("pages")),
                         "entry_point=%s pages=%d" % (man.get("entry_point"), len(man.get("pages", []))), "high"))
    sm = base.read_text("ia/sitemap-ia.xml") or ""
    n = sm.count("<loc>")
    checks.append(_check("sitemap-ia.xml présent et non vide", n > 0, "%d URLs" % n, "warn"))
    return checks


def _version_consistency():
    vj = S.load_json(base.repo_path("version.json"), default={}).get("version")
    build = base.read_text("scripts/build_ia.py") or ""
    m = re.search(r'VERSION\s*=\s*"([^"]+)"', build)
    bv = m.group(1) if m else None
    idx = base.read_text("ia/index.html") or ""
    fm = re.search(r"Vue IA v([0-9.]+)", idx)
    fv = fm.group(1) if fm else None
    return [_check("version.json présent", bool(vj), "version.json=%s" % vj, "high"),
            _check("cohérence version build_ia vs footer /ia", bv == fv, "build=%s footer=%s" % (bv, fv), "high")]


def _ia_regen_sync():
    rc, out, err = _run(["python", "scripts/build_ia.py"])
    checks = []
    cov = re.search(r"Couverture données\s*:\s*([0-9]+%|partielle)", out)
    routage = re.search(r"routage\s*—\s*(\d+)\s*tests.*?faux positifs contrats\s*:\s*([0-9]+)", out, re.S)
    checks.append(_check("générateur /ia s'exécute", rc == 0, (err or out)[-200:] if rc else "ok", "high"))
    if cov:
        checks.append(_check("couverture données = 100%", cov.group(1) == "100%", "couverture=%s" % cov.group(1), "high"))
    if routage:
        fp = int(routage.group(2))
        checks.append(_check("routage sans faux positif contrat", fp == 0, "tests=%s faux_positifs=%s" % (routage.group(1), fp), "high"))
    rc2, diffout, _ = _run(["git", "diff", "--name-only", "--", "ia"])
    changed = [l for l in diffout.splitlines() if l.strip()]
    checks.append(_check("sorties /ia publiées synchronisées", len(changed) == 0, "désynchronisés: %d" % len(changed), "high"))
    _run(["git", "checkout", "--", "ia"])
    metrics = {"coverage": (cov.group(1) if cov else "?"),
               "routing": ("%s tests, faux positifs %s" % (routage.group(1), routage.group(2)) if routage else "?")}
    return checks, metrics


def _dead_internal_links():
    files = sorted(glob.glob(base.repo_path("ia/*.html")))
    broken, total = [], 0
    for f in files:
        html = open(f, "r", encoding="utf-8", errors="ignore").read()
        for href in re.findall(r'href="([^"#?]+\.html)"', html):
            if href.startswith("http") or href.startswith("//") or ".." in href:
                continue
            total += 1
            target = os.path.normpath(os.path.join(os.path.dirname(f), href))
            if not os.path.isfile(target):
                broken.append("%s -> %s" % (os.path.basename(f), href))
    return _check("liens internes /ia valides", not broken, "cassés: %d %s" % (len(broken), broken[:5]), "high"), total, len(broken)


def _ia_pages_present():
    missing = [p for p in EXPECTED_IA_PAGES if not os.path.isfile(base.repo_path("ia/%s.html" % p))]
    return _check("pages IA attendues présentes", not missing, "manquantes: %s" % missing, "high")


def _notice_pdf():
    idx = S.load_json(base.repo_path("data/AXA/ia/axa_pdf_index.json"), default={})
    pdfs = idx.get("pdfs", []) if isinstance(idx, dict) else (idx or [])
    resolved = sum(1 for p in pdfs if os.path.isfile(base.repo_path(str(p.get("path", "")))))
    total = len(pdfs)
    return _check("notices PDF résolues sur disque", resolved == total, "%d/%d résolues" % (resolved, total), "warn"), total, total - resolved


def _ids():
    c = S.load_json(base.repo_path("ia/contrats.json"), default={})
    contrats = c.get("contrats", []) if isinstance(c, dict) else []
    ids = [x.get("id") for x in contrats]
    missing = sum(1 for i in ids if not i)
    dup = len(ids) - len(set(i for i in ids if i))
    checks = [_check("IDs contrats présents et uniques", missing == 0 and dup == 0,
                     "manquants=%d doublons=%d /%d" % (missing, dup, len(ids)), "high")]
    pv = S.load_json(base.repo_path("ia/preuves.json"), default={})
    items = pv.get("elements") or pv.get("preuves") or (pv if isinstance(pv, list) else [])
    pids = [e.get("id") for e in items if isinstance(e, dict) and e.get("id")]
    pdup = len(pids) - len(set(pids))
    checks.append(_check("IDs de preuves sans doublon", pdup == 0, "doublons=%d /%d" % (pdup, len(pids)), "warn"))
    def _has_src(e):
        if not isinstance(e, dict):
            return False
        src = e.get("src")
        loc = (src.get("document") or src.get("page")) if isinstance(src, dict) else src
        return bool(loc or e.get("source_pdf") or e.get("lien_notice") or e.get("page"))
    no_src = sum(1 for e in items if not _has_src(e))
    checks.append(_check("preuves avec source (document/notice)", no_src == 0, "sans source: %d /%d" % (no_src, len(items)), "warn"))
    return checks


def _cross_consistency():
    c = S.load_json(base.repo_path("ia/contrats.json"), default={})
    n_contr = len(c.get("contrats", [])) if isinstance(c, dict) else 0
    n_pages = len(glob.glob(base.repo_path("ia/contrat/*.html")))
    cov = S.load_json(base.repo_path("ia/matrices/couverture.json"), default={})
    if isinstance(cov, dict):
        n_cov = len(cov.get("contrats") or cov.get("rows") or cov.get("lignes") or [])
    else:
        n_cov = len(cov)
    counts = {"contrats.json": n_contr, "pages /ia/contrat": n_pages, "matrice couverture": n_cov}
    vals = [v for v in counts.values() if v]
    ok = len(set(vals)) <= 1 if vals else False
    return _check("cohérence des totaux contrats (JSON↔pages↔matrice)", ok, str(counts), "high")


def _orphans():
    files = glob.glob(base.repo_path("ia/*.html"))
    names = {os.path.basename(f) for f in files}
    linked = set()
    for f in files:
        html = open(f, "r", encoding="utf-8", errors="ignore").read()
        for href in re.findall(r'href="([^"#?/]+\.html)"', html):
            linked.add(href)
    orphans = sorted(n for n in names if n not in linked and n != "index.html")
    return _check("aucune page /ia orpheline", not orphans, "orphelines: %d %s" % (len(orphans), orphans[:5]), "warn"), orphans


def _pages_without_source():
    flagged = []
    for name in CATEGORY_PAGES:
        p = base.repo_path("ia/%s.html" % name)
        if not os.path.isfile(p):
            continue
        html = open(p, "r", encoding="utf-8", errors="ignore").read()
        if "<li" in html and "Notice" not in html and "notice" not in html:
            flagged.append(name)
    return _check("pages catégorie avec citations de notice", not flagged, "sans citation: %s" % flagged, "warn")


def run(ctx):
    ctx.self_wrote = True
    # Rapport précédent (avant d'écrire le nouveau) pour la comparaison d'état.
    prev_files = sorted(glob.glob(base.repo_path("agent-work/quality/reports/quality_*.json")))
    prev = S.load_json(prev_files[-1]) if prev_files else None
    prev_status = {c["name"]: c["ok"] for c in (prev.get("checks", []) if prev else [])}

    checks = []
    jv, n_json = _json_valid(); checks.append(jv)
    checks += _manifest_sitemap()
    checks += _version_consistency()
    sync_checks, sync_metrics = _ia_regen_sync(); checks += sync_checks
    dl, links_total, links_broken = _dead_internal_links(); checks.append(dl)
    checks.append(_ia_pages_present())
    npdf, notices_total, notices_unresolved = _notice_pdf(); checks.append(npdf)
    checks += _ids()
    checks.append(_cross_consistency())
    orph, orphans = _orphans(); checks.append(orph)
    checks.append(_pages_without_source())

    now_status = {c["name"]: c["ok"] for c in checks}
    failing = [c for c in checks if not c["ok"]]
    new_anom = [c for c in failing if prev_status.get(c["name"], True)]     # échoue, passait/absent avant
    known_anom = [c for c in failing if prev_status.get(c["name"]) is False]  # échoue déjà avant
    corrected = [n for n, ok in prev_status.items() if not ok and now_status.get(n) is True]

    pages_ia = len(glob.glob(base.repo_path("ia/*.html")))
    report = {
        "run_id": ctx.run_id, "agent_id": ctx.agent_id, "generated_at": S.now_iso(),
        "summary": {"total": len(checks), "passed": len(checks) - len(failing), "failed": len(failing),
                    "new_anomalies": len(new_anom), "known_anomalies": len(known_anom), "corrected": len(corrected)},
        "metrics": {"json_files_checked": n_json, "pages_ia": pages_ia, "links_checked": links_total,
                    "links_broken": links_broken, "notices_checked": notices_total,
                    "notices_unresolved": notices_unresolved, "orphan_pages": len(orphans),
                    **sync_metrics},
        "anomalies": {"new": [c["name"] for c in new_anom], "known": [c["name"] for c in known_anom], "corrected": corrected},
        "checks": checks,
    }
    stamp = S.stamp()
    report_rel = "agent-work/quality/reports/quality_%s.json" % stamp
    S.write_json(base.repo_path(report_rel), report)
    # Rapport Markdown court
    md = ["# Qualité Gabriel AXA — %s" % report["generated_at"], "",
          "%d/%d contrôles OK — %d anomalie(s) : %d nouvelle(s), %d connue(s), %d corrigée(s)." % (
              report["summary"]["passed"], report["summary"]["total"], len(failing),
              len(new_anom), len(known_anom), len(corrected)), ""]
    if failing:
        md.append("## Anomalies")
        for c in failing:
            state = "NOUVELLE" if c in new_anom else "connue"
            md.append("- [%s] **%s** — %s" % (state, c["name"], c["detail"]))
    if corrected:
        md.append("\n## Corrigées depuis le dernier run")
        md += ["- %s" % n for n in corrected]
    with open(base.repo_path("agent-work/quality/reports/quality_%s.md" % stamp), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    # Incidents structurés à IDENTIFIANT STABLE (pas d'accumulation ; les corrigés disparaissent).
    proposals, incidents_dir = [], base.repo_path("agent-work/quality/incidents")
    if not ctx.dry_run:
        for old in glob.glob(os.path.join(incidents_dir, "quality__*.json")):
            os.remove(old)  # repart de l'état courant : une anomalie corrigée n'a plus d'incident
    for c in failing:
        state = "nouvelle" if c in new_anom else "connue"
        p = base.new_proposal(
            ctx, task_type="quality", target={"file": "ia/", "section": c["name"]},
            source={"type": "repo", "document": "scripts/build_ia.py + ia/", "excerpt": c["detail"]},
            change={"operation": "report", "payload": {"check": c["name"], "detail": c["detail"],
                    "severity": c["severity"], "state": state}},
            reasoning="Contrôle qualité déterministe en échec (%s) : %s — %s" % (state, c["name"], c["detail"]),
            confidence=0.99, validation_required=True, origin="deterministic",
            risks=["signal de qualité ; aucune correction appliquée automatiquement"])
        p["proposal_id"] = "quality__" + re.sub(r"[^a-z0-9]+", "_", c["name"].lower()).strip("_")
        proposals.append(p)
        if not ctx.dry_run:
            S.write_json(os.path.join(incidents_dir, p["proposal_id"] + ".json"), p)

    ctx.summary = {
        "Pages IA analysées": pages_ia,
        "Fichiers JSON validés": n_json,
        "Liens contrôlés": links_total,
        "Liens cassés": links_broken,
        "Notices contrôlées": notices_total,
        "Chemins non résolus": notices_unresolved,
        "Pages orphelines": len(orphans),
        "Couverture Vue IA": sync_metrics.get("coverage", "?"),
        "Tests de routage": sync_metrics.get("routing", "?"),
        "Anomalies (nouv./connues/corr.)": "%d / %d / %d" % (len(new_anom), len(known_anom), len(corrected)),
        "Rapport": report_rel,
    }
    notes = ["qualité: %d/%d OK, %d nouvelle(s) anomalie(s)" % (report["summary"]["passed"], len(checks), len(new_anom))]
    return proposals, notes
