#!/usr/bin/env python3
"""Agent Coverage-gaps — DÉTERMINISTE (aucun LLM, aucune interprétation de PDF).

Exploite UNIQUEMENT les données déjà structurées (matrices de couverture, concepts) pour repérer des
trous : catégories absentes des données structurées d'un contrat, contrats sans notice, catégories peu
couvertes, concepts non reliés, écarts de couverture entre contrats.

Prudence absolue de formulation : il n'affirme JAMAIS qu'une donnée manque *dans le contrat*. Il dit
seulement « absente des données structurées », « non rendue dans la Vue IA » ou « vérification
documentaire humaine nécessaire ». Il ne corrige rien.
"""
import os, glob
import safety_checks as S
from agents import base

KEY_CATEGORIES = ["definitions", "exclusions", "conditions", "declencheurs"]  # trous les plus parlants


def _finding(ctx, kind, subject, detail, payload, confidence=0.85):
    return base.new_proposal(
        ctx, task_type="coverage",
        target={"file": "ia/matrices/couverture.json", "section": kind},
        source={"type": "derived", "document": "ia/matrices/couverture.json + ia/concepts.json",
                "excerpt": detail[:300]},
        change={"operation": "flag", "payload": {"gap": kind, "subject": subject, **payload}},
        reasoning=detail + " — Constat sur DONNÉES STRUCTURÉES uniquement (pas d'interprétation de la notice). "
                  "Vérification documentaire humaine nécessaire.",
        confidence=confidence, validation_required=True, origin="deterministic",
        risks=["ne signifie pas que la donnée manque dans le contrat : seulement absente des données structurées / de la Vue IA"])


def run(ctx):
    ctx.self_wrote = True
    cov = S.load_json(base.repo_path("ia/matrices/couverture.json"), default={})
    lignes = cov.get("lignes", []) if isinstance(cov, dict) else []
    cc = S.load_json(base.repo_path("ia/matrices/concepts-contrats.json"), default={})
    cc_lignes = cc.get("lignes", []) if isinstance(cc, dict) else []
    concepts = S.load_json(base.repo_path("ia/concepts.json"), default={}).get("concepts", {})
    pdfs = S.load_json(base.repo_path("data/AXA/ia/axa_pdf_index.json"), default={}).get("pdfs", [])

    proposals = []
    limit = ctx.limits.get("max_proposals_per_run", 5)

    # 1) Catégories-clés absentes des données structurées d'un contrat (compte == 0).
    for row in lignes:
        contrat = row.get("contrat", "?")
        zeros = [c for c in KEY_CATEGORIES if int(row.get(c, 0) or 0) == 0]
        if zeros:
            proposals.append(_finding(
                ctx, "categorie_absente_donnees", contrat,
                "Contrat « %s » : catégorie(s) %s absente(s) des données structurées." % (contrat, ", ".join(zeros)),
                {"contrat": contrat, "categories_absentes": zeros}, 0.9))

    # 2) Contrats sans notice (type document 'notice') dans l'index PDF.
    notice_contracts = {(p.get("nom_contrat") or "").strip().lower() for p in pdfs
                        if str(p.get("type_document", "")).lower().startswith("notice")}
    for row in lignes:
        contrat = row.get("contrat", "?")
        if contrat.strip().lower() not in notice_contracts:
            proposals.append(_finding(
                ctx, "contrat_sans_notice", contrat,
                "Contrat « %s » : aucune notice (type 'notice') trouvée dans l'index PDF structuré." % contrat,
                {"contrat": contrat}, 0.8))

    # 3) Catégories très peu couvertes globalement (présentes chez < 3 contrats).
    if lignes:
        cats = [c for c in (cov.get("colonnes") or [])]
        for cat in cats:
            present = sum(1 for r in lignes if int(r.get(cat, 0) or 0) > 0)
            if 0 < present < 3:
                proposals.append(_finding(
                    ctx, "categorie_peu_couverte", cat,
                    "Catégorie « %s » présente dans les données structurées de seulement %d/%d contrats." % (cat, present, len(lignes)),
                    {"categorie": cat, "contrats_couverts": present, "contrats_total": len(lignes)}, 0.7))

    # 4) Concepts non reliés à un contrat (ligne concept entièrement à zéro).
    for row in cc_lignes:
        concept = row.get("concept", "?")
        vals = [v for k, v in row.items() if k != "concept"]
        if vals and all(int(v or 0) == 0 for v in vals):
            proposals.append(_finding(
                ctx, "concept_non_relie", concept,
                "Concept « %s » : aucune occurrence structurée dans les contrats (matrice concepts×contrats)." % concept,
                {"concept": concept}, 0.75))

    # 5) Écart de couverture : contrats dont le total est très inférieur au maximum (< 30 %).
    totals = {r.get("contrat"): sum(int(v or 0) for k, v in r.items() if k != "contrat") for r in lignes}
    if totals:
        mx = max(totals.values()) or 1
        for contrat, tot in totals.items():
            if tot < 0.30 * mx:
                proposals.append(_finding(
                    ctx, "couverture_faible", contrat,
                    "Contrat « %s » : couverture structurée totale (%d) très inférieure au maximum (%d)." % (contrat, tot, mx),
                    {"contrat": contrat, "total": tot, "max": mx}, 0.7))

    proposals = proposals[:limit]
    # Identifiants stables + purge des anciens trous : incidents/ reflète l'état courant.
    import re
    for i, p in enumerate(proposals):
        subj = "%s_%s" % (p["proposed_change"]["payload"].get("gap", ""), p["proposed_change"]["payload"].get("subject", i))
        p["proposal_id"] = "coverage__" + re.sub(r"[^a-z0-9]+", "_", subj.lower()).strip("_")[:80]
    if not ctx.dry_run:
        out = base.repo_path("agent-work/quality/incidents")
        for old in glob.glob(os.path.join(out, "coverage__*.json")):
            os.remove(old)
        for p in proposals:
            S.write_json(os.path.join(out, p["proposal_id"] + ".json"), p)

    ctx.summary = {
        "Contrats analysés": len(lignes),
        "Concepts analysés": len(cc_lignes),
        "Trous détectés (données structurées)": len(proposals),
    }
    return proposals, ["coverage-gaps: %d trou(s) sur données structurées (aucune interprétation PDF)" % len(proposals)]
