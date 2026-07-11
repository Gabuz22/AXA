#!/usr/bin/env python3
"""Benchmark automatique des fournisseurs LLM gratuits — MESURE UNIQUEMENT.

Prend UNE micro-zone fixe et la fait traiter par chaque fournisseur gratuit disponible, avec le MÊME
prompt. Compare : temps, tokens, nb de propositions produites, nb VALIDES (passant la porte
déterministe anti-hallucination) => score de qualité. Met à jour agent-work/runs/provider_scores.json
(le routeur privilégiera ensuite le meilleur fournisseur). Ne produit AUCUNE proposition, ne modifie
aucune donnée métier ni master. À lancer tous les N runs (config providers.json: benchmark_every_runs)
ou manuellement. Sans clé API => rapport « aucun fournisseur ».

Usage : python agent-work/scripts/benchmark_providers.py [--zone-contract avizen] [--pages 3-5]
"""
import os, sys, time, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_checks as S
import quota_manager as Q
import provider_router as PR
from providers import adapters
from agents import extraction_llm as EX

BENCH_FILE = os.path.join(S.AGENT_WORK, "runs", "benchmark.json")
SCORES_FILE = os.path.join(S.AGENT_WORK, PR.SCORES_FILE)


def _fixed_zone(contract_hint, pages):
    """Choisit une micro-zone fixe et reproductible (mêmes pages pour tous les fournisseurs)."""
    idx = EX._pdf_index()
    entry = None
    for e in idx:
        if contract_hint in EX._norm(e.get("nom_contrat", "")) and str(e.get("type_document", "")).lower().startswith("notice"):
            entry = e; break
    entry = entry or (idx[0] if idx else None)
    if not entry:
        return None
    contrat = entry.get("nom_contrat", "?")
    pdf = EX._resolve_pdf(entry)
    if not pdf:
        return None
    start, end = pages
    page_texts = EX._read_pdf_pages(pdf, start, end)
    if not page_texts:
        return None
    gap = EX._gap_categories(contrat)
    prompt = EX._build_prompt(contrat, page_texts, gap, EX._labels_for(EX._norm(contrat).replace(" ", "-"), gap),
                              {c: EX._peers_covering(c, contrat) for c in gap})
    return {"contrat": contrat, "page_texts": page_texts, "prompt": prompt}


def _score_provider(router, pid, prompt, page_texts):
    """Appelle un fournisseur précis et mesure. Retourne un dict de mesure (jamais de secret)."""
    p = router.cfg["providers"][pid]
    style = adapters.STYLES[p["style"]]
    key = router._key_for(p); acc = router._account_for(p)
    model = (p.get("models") or [p.get("model")])[0]
    pcfg = dict(p); pcfg["model"] = model
    messages = [{"role": "system", "content": S.SYSTEM_DATA_ONLY_RULE + " Reponds UNIQUEMENT en JSON."},
                {"role": "user", "content": prompt}]
    t0 = time.time()
    try:
        text, tin, tout = style(pcfg, key, acc, messages, 900, 20)
    except Exception as e:
        return {"provider": pid, "model": model, "ok": False, "error": S.redact_secrets(str(e), router.cfg)[:120],
                "time_s": round(time.time() - t0, 2), "produced": 0, "valid": 0, "quality": 0}
    dt = round(time.time() - t0, 2)
    from agents.base import extract_json_block
    data = extract_json_block(text) or {}
    items = data.get("items", []) if isinstance(data, dict) else []
    valid = sum(1 for it in items if EX.check_extraction(it, page_texts, EX.CATEGORIES, set())[0])
    quality = round(100.0 * valid / max(1, len(items)), 1) if items else 0.0
    return {"provider": pid, "model": model, "ok": True, "time_s": dt, "tokens_in": tin, "tokens_out": tout,
            "produced": len(items), "valid": valid, "quality": quality}


def run(contract_hint="avizen", pages=(3, 5)):
    cfg = S.load_providers_config(); pol = S.load_policies()
    S.preflight(pol, cfg, need_llm=True)  # fail-closed : jamais payant/carte
    router = PR.ProviderRouter(cfg, pol)
    providers = router.available()
    if not providers:
        print("[benchmark] Aucun fournisseur gratuit disponible (configurez au moins une clé). Rien à mesurer.")
        return {"generated_at": S.now_iso(), "results": [], "note": "aucun fournisseur"}
    zone = _fixed_zone(contract_hint, pages)
    if not zone:
        print("[benchmark] Zone fixe indisponible (pypdf ou notice manquante).")
        return {"generated_at": S.now_iso(), "results": [], "note": "zone indisponible"}

    results = [_score_provider(router, pid, zone["prompt"], zone["page_texts"]) for pid in providers]
    results.sort(key=lambda r: (-r.get("quality", 0), r.get("time_s", 999)))
    report = {"generated_at": S.now_iso(), "contrat": zone["contrat"], "pages": list(pages), "results": results}
    S.write_json(BENCH_FILE, report)

    # Met à jour la qualité apprise (le routeur s'en sert pour l'ordre). Aucune donnée métier touchée.
    sc = S.load_json(SCORES_FILE, default={"providers": {}})
    for r in results:
        if r.get("ok"):
            s = sc["providers"].setdefault(r["provider"], {"quality": 50.0, "success": 0, "error": 0})
            n = int(s.get("samples", 0))
            s["quality"] = round((s["quality"] * n + r["quality"]) / (n + 1), 1)  # moyenne glissante
            s["samples"] = n + 1
    sc["updated_at"] = S.now_iso()
    S.write_json(SCORES_FILE, sc)

    print("== Benchmark fournisseurs (zone fixe : %s p.%d-%d) ==" % (zone["contrat"], pages[0], pages[1]))
    for r in results:
        if r.get("ok"):
            print("  %-12s qualité=%.0f valides=%d/%d temps=%.2fs tok=%d/%d" % (
                r["provider"], r["quality"], r["valid"], r["produced"], r["time_s"], r.get("tokens_in", 0), r.get("tokens_out", 0)))
        else:
            print("  %-12s ERREUR %s" % (r["provider"], r.get("error")))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone-contract", default="avizen")
    ap.add_argument("--pages", default="3-5")
    a = ap.parse_args()
    try:
        s, e = (int(x) for x in a.pages.split("-"))
    except Exception:
        s, e = 3, 5
    run(a.zone_contract, (s, e))
