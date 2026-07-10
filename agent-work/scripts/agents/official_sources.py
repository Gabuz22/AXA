#!/usr/bin/env python3
"""Agent Sources officielles — DÉTERMINISTE. Vérifie les liens officiels suivis, conserve des
empreintes (snapshots), produit un comparatif avant/après. N'interprète JAMAIS une règle juridique
et ne déclare jamais une règle actuelle : toute évolution est signalée pour validation humaine.

Statuts : changement_technique | changement_editorial | changement_potentiellement_reglementaire |
source_indisponible | validation_humaine_requise.
"""
import os, re, hashlib, urllib.request, urllib.error
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


def _fetch_hash(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "GabrielAXA-agent/1.0 (+monitoring)"} , method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read(200000)
    text = body.decode("utf-8", "ignore")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), len(text)


def _snap_path(url):
    return base.repo_path(os.path.join(SNAP_DIR, S.content_hash(url)[:16] + ".json"))


def _example(ctx):
    return base.new_proposal(
        ctx, task_type="official-source",
        target={"file": "ia/sources-officielles.json", "section": "autorites"},
        source={"type": "url", "url": "https://www.service-public.fr/", "document": "service-public.fr",
                "excerpt": "[EXEMPLE] empreinte de page — comparaison avant/apres"},
        change={"operation": "flag", "payload": {"status": "changement_technique", "before_hash": "abc123", "after_hash": "def456"}},
        reasoning="Exemple de detection de changement d'empreinte (aucun reseau). Aucune interpretation reglementaire.",
        confidence=0.9, validation_required=True, regulatory_status="changement_technique", origin="example_fixture",
        risks=["ne jamais interpreter une regle ; validation humaine requise si contenu reglementaire"],
    )


def run(ctx):
    if ctx.mock:
        return [_example(ctx)], ["sources: exemple (mock, aucun reseau)"]

    policies = ctx.policies
    timeout = policies.get("limits", {}).get("http_timeout_seconds", 20)
    proposals, notes = [], []
    for url in _tracked_urls(ctx)[: ctx.limits.get("max_proposals_per_run", 5)]:
        if not S.url_allowed(url, policies, require_official=True):
            notes.append("ignore (hors allowlist officielle): %s" % url)
            continue
        snap_p = _snap_path(url)
        prev = S.load_json(snap_p, default=None)
        try:
            h, size = _fetch_hash(url, timeout)
        except Exception as e:
            proposals.append(base.new_proposal(
                ctx, task_type="official-source", target={"file": "ia/sources-officielles.json"},
                source={"type": "url", "url": url, "document": url, "excerpt": "source indisponible"},
                change={"operation": "flag", "payload": {"status": "source_indisponible"}},
                reasoning="Source injoignable au moment du run (%s)." % S.redact_secrets(str(e), {"providers": {}}),
                confidence=0.8, validation_required=True, regulatory_status="source_indisponible"))
            continue
        if prev is None:
            if not ctx.dry_run:
                S.write_json(snap_p, {"url": url, "hash": h, "size": size, "seen_at": S.now_iso()})
            notes.append("snapshot initial: %s" % url)
            continue
        if prev.get("hash") != h:
            status = "changement_potentiellement_reglementaire" if any(
                k in url for k in ("bofip", "legifrance", "impots")) else "changement_editorial"
            p = base.new_proposal(
                ctx, task_type="official-source", target={"file": "ia/sources-officielles.json"},
                source={"type": "url", "url": url, "document": url, "excerpt": "empreinte modifiee"},
                change={"operation": "flag", "payload": {"status": status, "before_hash": prev.get("hash"), "after_hash": h}},
                reasoning="Empreinte de contenu modifiee depuis le dernier snapshot. Aucune interpretation effectuee.",
                confidence=0.85, validation_required=True, regulatory_status=status,
                risks=["interpretation reglementaire interdite ; validation humaine requise"])
            proposals.append(p)
            if not ctx.dry_run:
                S.write_json(base.repo_path(os.path.join(CHANGES_DIR, p["proposal_id"] + ".json")), p)
                S.write_json(snap_p, {"url": url, "hash": h, "size": size, "seen_at": S.now_iso()})
    return proposals, notes or ["sources: aucun changement detecte"]
