#!/usr/bin/env python3
"""Cartographie AUTOMATIQUE du projet — générée depuis le code réel (imports, workflows, artefacts).

Produit agent-work/CARTOGRAPHIE.md : qui importe quoi (agents→moteurs→graphe→projections),
workflows→agents→branches, artefacts persistants, fichiers curés. Regénérer après tout changement :
    python agent-work/scripts/generate_map.py
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "agent-work", "CARTOGRAPHIE.md")

CORE_GENERIC = {"knowledge_graph", "coverage_model", "knowledge_ops", "knowledge_tasks", "knowledge_build",
                "knowledge_status", "knowledge_review", "knowledge_manager", "knowledge_compare",
                "knowledge_projection", "change_detect", "corpus_intel", "domain_adapter", "orch",
                "inspector_case", "inspector_needs", "inspector_mono", "inspector_multi",
                "inspector_solution", "inspector_advice", "inspector_bench", "inspector_projection",
                "commercial_kit", "claude_harness"}
AXA_SPECIFIC = {"claude_enrichment"}  # charge les fichiers d'enrichment AXA (le module est ~générique, le contenu non)


def scan_imports():
    deps = {}
    for root, _dirs, files in os.walk(os.path.join(REPO, "agent-work", "scripts")):
        if "__pycache__" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(root, f), os.path.join(REPO, "agent-work", "scripts")).replace("\\", "/")
            try:
                src = open(os.path.join(root, f), encoding="utf-8").read()
            except Exception:
                continue
            mods = set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", src, re.M))
            local = {m.split(".")[0] for m in mods} & (CORE_GENERIC | AXA_SPECIFIC |
                     {"safety_checks", "provider_router", "quota_manager", "validate_proposal", "deduplicate",
                      "select_task", "restore_state", "orchestrator", "orchestrator_cycle", "environment_ingest",
                      "knowledge_ingest"})
            deps[rel] = sorted(local - {rel[:-3]})
    return deps


def scan_workflows():
    wf = {}
    d = os.path.join(REPO, ".github", "workflows")
    for f in sorted(os.listdir(d)):
        if not f.endswith(".yml"):
            continue
        src = open(os.path.join(d, f), encoding="utf-8").read()
        agent = re.search(r"agent:\s*([\w-]+)", src)
        cron = re.findall(r'cron:\s*"([^"]+)"', src)
        mode = re.search(r"mode:\s*(\w+)", src)
        wf[f] = {"agent": agent.group(1) if agent else None,
                 "mode": mode.group(1) if mode else None,
                 "crons": [c for c in cron]}
    return wf


def main():
    deps = scan_imports()
    wf = scan_workflows()
    L = ["# Cartographie Gabriel AXA (générée par generate_map.py — ne pas éditer à la main)", ""]
    L.append("## Workflows → agents (branche cible : agents/proposals via _agents-run.yml ; jamais de merge auto)")
    for f, w in wf.items():
        L.append("- `%s` → agent=%s mode=%s cron=%s" % (f, w["agent"] or "—", w["mode"] or "agent", ",".join(w["crons"]) or "manuel"))
    L.append("\n## Agents → dépendances (imports réels)")
    for rel in sorted(d for d in deps if d.startswith("agents/") and not d.endswith("__init__.py")):
        L.append("- `%s` → %s" % (rel, ", ".join(deps[rel]) or "—"))
    L.append("\n## Moteurs génériques (noyau réutilisable Gabriel Virtuel) → dépendances")
    for rel in sorted(deps):
        name = os.path.basename(rel)[:-3]
        if name in CORE_GENERIC and not rel.startswith(("agents/", "tests/")):
            L.append("- `%s` → %s" % (rel, ", ".join(deps[rel]) or "—"))
    L.append("\n## Adaptateur & contenu AXA")
    L.append("- `domains/axa.py` (adaptateur), `agent-work/enrichment/*.json` (sémantique/métier/expérience étiquetées),")
    L.append("  `config/*.json`, masters `ia/` + `data/AXA/` (lecture seule pour les agents).")
    L.append("\n## Artefacts persistants (restaurés depuis agents/proposals — voir restore_state.PERSISTENT)")
    src = open(os.path.join(REPO, "agent-work", "scripts", "restore_state.py"), encoding="utf-8").read()
    for p in re.findall(r'"(agent-work/[^"]+)"', src):
        L.append("- `%s`" % p)
    L.append("\n## Chaîne de production")
    L.append("```")
    L.append("masters + notices PDF")
    L.append("  → domains/axa (adaptateur) → knowledge_ingest + environment_ingest + claude_enrichment (étiqueté)")
    L.append("  → knowledge_graph (L1 preuves / L2 entités / L3 relations / L4 compréhension + statuts)")
    L.append("  → coverage_model (profondeur) → knowledge_tasks (backlog vivant) → knowledge-builder (LLM, gaté)")
    L.append("  → inspector_* (fiches, multi, cas, avis, kit) + knowledge_review/manager/compare")
    L.append("  → scripts/build_inspector_ia.py → ia/inspecteur/ (Vue IA publique, lecture seule)")
    L.append("```")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("CARTOGRAPHIE.md : %d workflows, %d modules cartographiés" % (len(wf), len(deps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
