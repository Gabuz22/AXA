#!/usr/bin/env python3
"""Agent UX de la Vue IA — DÉTERMINISTE. Analyse la navigation statique : pages orphelines (jamais
liées), liens trop profonds, incohérences. NE MODIFIE PAS la Vue IA : propose de petites améliorations.
"""
import os, re, glob
import safety_checks as S
from agents import base


def _orphans_and_stats():
    files = glob.glob(base.repo_path("ia/*.html"))
    names = {os.path.basename(f) for f in files}
    linked = set()
    for f in files:
        try:
            html = open(f, "r", encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for href in re.findall(r'href="([^"#?]+\.html)"', html):
            if "/" not in href and ".." not in href:
                linked.add(href)
    orphans = sorted(n for n in names if n not in linked and n != "index.html")
    return orphans, len(files)


def run(ctx):
    orphans, total = _orphans_and_stats()
    proposals = []
    for name in orphans[: ctx.limits.get("max_proposals_per_run", 5)]:
        proposals.append(base.new_proposal(
            ctx, task_type="ux",
            target={"file": "ia/index.html", "section": "navigation"},
            source={"type": "repo", "document": "ia/%s" % name, "excerpt": "page non liee depuis les autres pages /ia"},
            change={"operation": "flag", "payload": {"issue": "page_orpheline", "page": name,
                    "suggestion": "ajouter un lien vers %s depuis l'index ou la nav" % name}},
            reasoning="Page /ia potentiellement orpheline (aucun lien interne detecte). Suggestion de navigation ; Vue IA non modifiee.",
            confidence=0.7, validation_required=True))
    notes = ["ux: %d page(s) orpheline(s) sur %d" % (len(orphans), total)]
    if not proposals and ctx.mock:
        proposals.append(base.new_proposal(
            ctx, task_type="ux", target={"file": "ia/index.html", "section": "navigation"},
            source={"type": "repo", "document": "ia/", "excerpt": "[EXEMPLE] aucune page orpheline detectee"},
            change={"operation": "flag", "payload": {"issue": "exemple", "suggestion": "aucune amelioration UX critique"}},
            reasoning="Exemple : navigation /ia coherente (aucune page orpheline). Format de suggestion UX.",
            confidence=0.6, validation_required=True, origin="example_fixture"))
        notes.append("ux: exemple (mock)")
    return proposals, notes
