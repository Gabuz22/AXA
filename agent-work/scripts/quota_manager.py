#!/usr/bin/env python3
"""Gestion du budget par run et de l'arrêt propre sur épuisement de quota.

- Budget : plafonds d'appels LLM et de tokens (estimés) pour UN run. Dépassement => QuotaExhausted.
- Cooldowns fournisseurs : un provider ayant renvoyé 429 est mis en pause (état persistant léger),
  pour ne pas le re-solliciter inutilement le même jour.
Aucune dépense n'est jamais engagée : la gratuité est une capacité configurable, vérifiée à l'exécution.
"""
import os, json, time, datetime
import safety_checks as S

STATE_FILE = os.path.join(S.AGENT_WORK, "runs", "quota_state.json")


class QuotaExhausted(Exception):
    """Levée quand le budget du run est atteint : l'agent doit s'arrêter proprement."""


class Budget:
    def __init__(self, max_llm_calls, max_tokens):
        self.max_llm_calls = int(max_llm_calls)
        self.max_tokens = int(max_tokens)
        self.llm_calls = 0
        self.tokens_in = 0
        self.tokens_out = 0

    def can_spend(self, est_tokens=0):
        return (self.llm_calls < self.max_llm_calls) and (self.tokens_in + self.tokens_out + est_tokens <= self.max_tokens)

    def before_call(self, est_in_tokens):
        if self.llm_calls >= self.max_llm_calls:
            raise QuotaExhausted("plafond d'appels LLM atteint (%d)" % self.max_llm_calls)
        if self.tokens_in + self.tokens_out + est_in_tokens > self.max_tokens:
            raise QuotaExhausted("plafond de tokens atteint (%d)" % self.max_tokens)

    def record(self, tokens_in, tokens_out):
        self.llm_calls += 1
        self.tokens_in += int(tokens_in or 0)
        self.tokens_out += int(tokens_out or 0)

    def as_counters(self):
        return {"llm_calls": self.llm_calls, "tokens_in_est": self.tokens_in, "tokens_out_est": self.tokens_out}


def _load_state():
    return S.load_json(STATE_FILE, default={"cooldowns": {}})


def _save_state(state, dry_run):
    if dry_run:
        return
    S.write_json(STATE_FILE, state)


def provider_in_cooldown(provider_id):
    state = _load_state()
    until = state.get("cooldowns", {}).get(provider_id)
    if not until:
        return False
    try:
        return time.time() < float(until)
    except (TypeError, ValueError):
        return False


def set_cooldown(provider_id, seconds, dry_run=False):
    state = _load_state()
    state.setdefault("cooldowns", {})[provider_id] = time.time() + seconds
    state["updated_at"] = S.now_iso()
    _save_state(state, dry_run)


def estimate_tokens(text):
    """Estimation grossière : ~4 caractères par token."""
    return max(1, len(text or "") // 4)
