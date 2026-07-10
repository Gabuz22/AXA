#!/usr/bin/env python3
"""Agent Sources officielles — DÉTERMINISTE (réseau, aucun LLM).

Vérifie le statut HTTP des URLs suivies, détecte redirections et changements d'URL, enregistre code
HTTP / URL finale / date / empreinte, compare à l'empreinte précédente, signale erreurs réseau/cert.
Classe UNIQUEMENT (jamais d'interprétation) : indisponible | redirection | contenu_modifie |
contenu_inchange | verification_humaine_requise. Ne modifie jamais une règle publiée.
"""
import os, re, ssl, hashlib, urllib.request, urllib.error
import safety_checks as S
from agents import base

SNAP_DIR = "agent-work/official-sources/snapshots"
CHANGES_DIR = "agent-work/official-sources/changes"


def _tracked_urls(ctx):
    urls = list((ctx.task or {}).get("read_urls") or [])
    src = S.load_json(base.repo_path("ia/sources-officielles.json"), default={})
    for a in (src.get("autorites") or src.get("sources") or []):
        u = a.get("url") if isinstance(a, dict) else None
        if u:
            urls.append(u)
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def _fetch(url, timeout):
    """Retourne (status, final_url, fingerprint, size) ou lève."""
    req = urllib.request.Request(url, headers={"User-Agent": "GabrielAXA-agent/1.0 (+monitoring)"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        status = getattr(r, "status", 200)
        final_url = r.geturl()
        body = r.read(200000)
    text = body.decode("utf-8", "ignore")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return status, final_url, hashlib.sha256(text.encode("utf-8")).hexdigest(), len(text)


def _snap_path(url):
    return base.repo_path(os.path.join(SNAP_DIR, S.content_hash(url)[:16] + ".json"))


def _proposal(ctx, url, kind, payload, reg_status):
    return base.new_proposal(
        ctx, task_type="official-source", target={"file": "ia/sources-officielles.json", "section": "autorites"},
        source={"type": "url", "url": url, "document": url, "excerpt": "surveillance technique: %s" % kind},
        change={"operation": "flag", "payload": {"change_kind": kind, **payload}},
        reasoning="Surveillance technique d'une source officielle (%s). Aucune interprétation du contenu ; "
                  "aucune règle publiée modifiée." % kind,
        confidence=0.85, validation_required=True, regulatory_status=reg_status,
        risks=["interprétation réglementaire interdite ; validation humaine requise"])


def _example(ctx):
    return base.new_proposal(
        ctx, task_type="official-source", target={"file": "ia/sources-officielles.json", "section": "autorites"},
        source={"type": "url", "url": "https://www.service-public.fr/", "document": "service-public.fr", "excerpt": "[EXEMPLE]"},
        change={"operation": "flag", "payload": {"change_kind": "contenu_inchange", "http_status": 200}},
        reasoning="Exemple de surveillance (mock, aucun réseau). Aucune interprétation.",
        confidence=0.6, validation_required=True, regulatory_status="none", origin="example_fixture")


def run(ctx):
    if ctx.mock:
        ctx.summary = {"Mode": "mock (aucun réseau)"}
        return [_example(ctx)], ["sources: exemple (mock)"]

    policies, timeout = ctx.policies, ctx.policies.get("limits", {}).get("http_timeout_seconds", 20)
    proposals, checked, changed, unavailable, redirects = [], 0, 0, 0, 0
    for url in _tracked_urls(ctx)[: max(10, ctx.limits.get("max_proposals_per_run", 5) * 3)]:
        if not S.url_allowed(url, policies, require_official=True):
            continue
        checked += 1
        snap_p = _snap_path(url)
        prev = S.load_json(snap_p, default=None)
        try:
            status, final_url, fp, size = _fetch(url, timeout)
        except (urllib.error.URLError, ssl.SSLError, Exception) as e:
            unavailable += 1
            proposals.append(_proposal(ctx, url, "indisponible", {"error": S.redact_secrets(str(e), {"providers": {}})[:120]}, "source_indisponible"))
            continue
        gov = any(k in url for k in ("legifrance", "bofip", "impots"))
        if status >= 400:
            unavailable += 1
            proposals.append(_proposal(ctx, url, "indisponible", {"http_status": status}, "source_indisponible"))
            continue
        redirected = final_url.rstrip("/") != url.rstrip("/")
        if redirected:
            redirects += 1
            proposals.append(_proposal(ctx, url, "redirection", {"http_status": status, "final_url": final_url}, "validation_humaine_requise"))
        snap = {"url": url, "final_url": final_url, "http_status": status, "hash": fp, "size": size, "seen_at": S.now_iso()}
        if prev is None:
            if not ctx.dry_run:
                S.write_json(snap_p, snap)
            continue
        if prev.get("hash") != fp:
            changed += 1
            reg = "validation_humaine_requise" if gov else "changement_editorial"
            p = _proposal(ctx, url, "contenu_modifie", {"http_status": status, "before_hash": prev.get("hash"), "after_hash": fp}, reg)
            proposals.append(p)
            if not ctx.dry_run:
                S.write_json(base.repo_path(os.path.join(CHANGES_DIR, p["proposal_id"] + ".json")), p)
                S.write_json(snap_p, snap)
    ctx.summary = {"URLs suivies contrôlées": checked, "Contenus modifiés": changed,
                   "Redirections": redirects, "Indisponibles": unavailable}
    return proposals, ["sources: %d contrôlées, %d modifiées, %d redirections, %d indisponibles" % (checked, changed, redirects, unavailable)]
