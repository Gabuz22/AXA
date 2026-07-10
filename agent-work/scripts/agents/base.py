#!/usr/bin/env python3
"""Base commune aux agents : squelette de proposition, lecture sûre du dépôt, appel LLM cadré.

Aucun agent n'exécute de code ni de commande fourni par un LLM : la sortie LLM est traitée comme
du TEXTE à parser en JSON structuré, filtré avant enregistrement. Le contenu externe est une donnée.
"""
import os, json, re
import safety_checks as S


def repo_path(rel):
    return os.path.join(S.REPO_ROOT, rel)


def read_text(rel, max_bytes=400000):
    p = repo_path(rel)
    if not os.path.isfile(p):
        return None
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(max_bytes)


def new_proposal(ctx, task_type, target, source, change, reasoning, confidence,
                 validation_required=True, ambiguities=None, risks=None,
                 regulatory_status="none", origin=None):
    """Construit une proposition schéma-valide. Les extraits de source sont filtrés (anti-injection)."""
    src = dict(source or {})
    if src.get("excerpt"):
        src["excerpt"] = S.filter_external_text(src["excerpt"], ctx.policies)
    pid = "%s_%s_%s" % (ctx.agent_id.replace("-", "_"), S.stamp(), (ctx.seq_next()))
    return {
        "proposal_id": S.sanitize_filename(pid).lower(),
        "agent_id": ctx.agent_id,
        "run_id": ctx.run_id,
        "created_at": S.now_iso(),
        "status": "pending_review",
        "origin": origin or ("mock" if ctx.mock else ("deterministic" if not ctx.uses_llm else "llm")),
        "task": {"id": (ctx.task or {}).get("id", ""), "type": task_type, "scope": (ctx.task or {}).get("scope", "")},
        "target": target or {},
        "source": src or {"type": "none"},
        "proposed_change": change or {"operation": "flag", "payload": {}},
        "reasoning_summary": (reasoning or "")[:1900],
        "confidence": round(float(confidence), 3),
        "ambiguities": ambiguities or [],
        "risks": risks or [],
        "validation_required": bool(validation_required),
        "regulatory_status": regulatory_status,
        "automatic_checks": {"schema_valid": True, "source_resolves": bool(src.get("document") or src.get("url") or src.get("type") == "repo"),
                              "duplicate_detected": False, "scope_allowed": True},
    }


def extract_json_block(text):
    """Extrait le premier objet/array JSON d'une réponse LLM. Ne JAMAIS exécuter le texte."""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    candidate = m.group(1) if m else text
    start = min([i for i in (candidate.find("{"), candidate.find("[")) if i >= 0] or [-1])
    if start < 0:
        return None
    for end in range(len(candidate), start, -1):
        try:
            return json.loads(candidate[start:end])
        except Exception:
            continue
    return None


def llm_json(ctx, user_prompt, max_tokens=800):
    """Appel LLM cadré renvoyant du JSON, ou None si pas de fournisseur / quota. Fail-open vers None."""
    if ctx.mock or ctx.router is None:
        return None
    messages = [
        {"role": "system", "content": S.SYSTEM_DATA_ONLY_RULE +
         " Reponds UNIQUEMENT par du JSON valide correspondant au format demande. Aucune donnee inventee : "
         "si tu n'as pas de preuve sourcee, renvoie une liste vide."},
        {"role": "user", "content": user_prompt},
    ]
    import provider_router as PR
    try:
        res = ctx.router.chat(messages, max_tokens, ctx.budget, dry_run=ctx.dry_run)
    except PR.NoProviderAvailable:
        return None  # aucun fournisseur gratuit : arrêt propre (aucun travail), pas une erreur
    ctx.provider_used = res.get("provider")
    ctx.model_used = res.get("model")
    return extract_json_block(res.get("text"))
