#!/usr/bin/env python3
"""Adaptateurs HTTP vers les fournisseurs LLM gratuits (stdlib urllib uniquement).

Chaque style d'API (openai, gemini, cloudflare) est isolé. Aucun quota/modèle/URL codé en dur ici :
tout vient de providers.json. Les erreurs 429 / quota sont remontées via RateLimited pour que le
routeur bascule ou s'arrête proprement. Les secrets ne sont jamais journalisés.
"""
import json, urllib.request, urllib.error


class RateLimited(Exception):
    """429 ou quota épuisé côté fournisseur."""
    def __init__(self, msg, code=429):
        super().__init__(msg); self.code = code


class ProviderError(Exception):
    """Autre erreur (réseau, 4xx/5xx). `.code` = statut HTTP (0 si réseau/timeout)."""
    def __init__(self, msg, code=0):
        super().__init__(msg); self.code = code


def _post(url, headers, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        code = e.code
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")[:300]
        except Exception:
            pass
        if code == 429 or "quota" in body.lower() or "rate" in body.lower():
            raise RateLimited("HTTP %d" % code, code=429)
        raise ProviderError("HTTP %d: %s" % (code, body), code=code)
    except urllib.error.URLError as e:
        raise ProviderError("réseau: %s" % e, code=0)


def openai_chat(cfg, api_key, account_id, messages, max_tokens, timeout):
    """Style OpenAI-compatible : Groq, OpenRouter (modèles ':free' uniquement)."""
    url = cfg["base_url"].rstrip("/") + cfg.get("path", "/chat/completions")
    headers = {"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"}
    payload = {"model": cfg["model"], "messages": messages,
               "max_tokens": min(max_tokens, cfg.get("max_output_tokens", 1024)), "temperature": 0.2}
    resp = _post(url, headers, payload, timeout)
    text = ((resp.get("choices") or [{}])[0].get("message") or {}).get("content", "") or ""
    usage = resp.get("usage") or {}
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def gemini_chat(cfg, api_key, account_id, messages, max_tokens, timeout):
    """Google Gemini generateContent."""
    path = cfg.get("path", "/v1beta/models/{model}:generateContent").replace("{model}", cfg["model"])
    url = cfg["base_url"].rstrip("/") + path + "?key=" + api_key
    sys_txt = "\n".join(m["content"] for m in messages if m["role"] == "system")
    user_txt = "\n".join(m["content"] for m in messages if m["role"] != "system")
    payload = {"contents": [{"parts": [{"text": user_txt}]}],
               "generationConfig": {"maxOutputTokens": min(max_tokens, cfg.get("max_output_tokens", 1024)), "temperature": 0.2}}
    if sys_txt:
        payload["systemInstruction"] = {"parts": [{"text": sys_txt}]}
    resp = _post(url, {"Content-Type": "application/json"}, payload, timeout)
    cand = (resp.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in ((cand.get("content") or {}).get("parts") or []))
    um = resp.get("usageMetadata") or {}
    return text, um.get("promptTokenCount", 0), um.get("candidatesTokenCount", 0)


def cloudflare_chat(cfg, api_key, account_id, messages, max_tokens, timeout):
    """Cloudflare Workers AI."""
    if not account_id:
        raise ProviderError("CLOUDFLARE_ACCOUNT_ID manquant")
    path = cfg.get("path").replace("{account_id}", account_id).replace("{model}", cfg["model"])
    url = cfg["base_url"].rstrip("/") + path
    headers = {"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"}
    payload = {"messages": messages, "max_tokens": min(max_tokens, cfg.get("max_output_tokens", 1024))}
    resp = _post(url, headers, payload, timeout)
    result = resp.get("result") or {}
    text = result.get("response", "") if isinstance(result, dict) else ""
    return text, 0, 0


STYLES = {"openai": openai_chat, "gemini": gemini_chat, "cloudflare": cloudflare_chat}
