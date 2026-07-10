#!/usr/bin/env python3
"""Routeur multi-fournisseurs : choisit un fournisseur gratuit disponible, respecte le budget,
gère les 429, bascule éventuellement, s'arrête proprement si aucun quota gratuit n'est disponible.

Ne journalise QUE : fournisseur, modèle, tokens estimés, statut. Jamais les secrets.
Un fournisseur n'est éligible que si : enabled ET free_tier ET non requires_paid ET clé présente
dans l'environnement ET pas en cooldown. `allow_paid_usage` doit rester false (vérifié en préflight).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_checks as S
import quota_manager as Q
from providers import adapters


class NoProviderAvailable(Exception):
    """Aucun fournisseur gratuit utilisable (clés absentes, tous en cooldown, ou aucun activé)."""


class ProviderRouter:
    def __init__(self, providers_cfg, policies, logger=None):
        self.cfg = providers_cfg
        self.policies = policies
        self.log = logger or (lambda m: print(m))

    def _key_for(self, p):
        env = p.get("api_key_env")
        return os.environ.get(env) if env else None

    def available(self):
        """Liste ordonnée des ids de fournisseurs réellement utilisables (sans exposer les clés)."""
        order = self.cfg.get("default_order") or list(self.cfg.get("providers", {}).keys())
        out = []
        for pid in order:
            p = self.cfg.get("providers", {}).get(pid)
            if not p or not p.get("enabled"):
                continue
            if not p.get("free_tier") or p.get("requires_paid"):
                continue
            if not self._key_for(p):
                continue
            if Q.provider_in_cooldown(pid):
                continue
            out.append(pid)
        return out

    def chat(self, messages, max_tokens, budget, dry_run=False):
        """Tente chaque fournisseur disponible. Retourne un dict de résultat ou lève.

        - QuotaExhausted si le budget du run est atteint (arrêt propre).
        - NoProviderAvailable si aucun fournisseur gratuit n'est utilisable.
        """
        est_in = Q.estimate_tokens("\n".join(m.get("content", "") for m in messages))
        budget.before_call(est_in)  # peut lever QuotaExhausted

        providers = self.available()
        if not providers:
            raise NoProviderAvailable("aucun fournisseur gratuit disponible (clés absentes / cooldown / désactivés)")

        last_err = None
        for pid in providers:
            p = self.cfg["providers"][pid]
            style = adapters.STYLES.get(p.get("style"))
            if not style:
                continue
            key = self._key_for(p)
            account_id = os.environ.get(p.get("account_id_env")) if p.get("account_id_env") else None
            timeout = self.policies.get("limits", {}).get("http_timeout_seconds", 20)
            try:
                text, tin, tout = style(p, key, account_id, messages, max_tokens, timeout)
                tin = tin or est_in
                tout = tout or Q.estimate_tokens(text)
                budget.record(tin, tout)
                self.log("[provider] used=%s model=%s tokens_in~%d tokens_out~%d status=ok" % (pid, p["model"], tin, tout))
                return {"text": text, "provider": pid, "model": p["model"], "tokens_in": tin, "tokens_out": tout}
            except adapters.RateLimited as e:
                self.log("[provider] used=%s model=%s status=rate_limited (%s) -> cooldown+bascule" % (pid, p["model"], e))
                Q.set_cooldown(pid, seconds=6 * 3600, dry_run=dry_run)
                last_err = e
                continue
            except adapters.ProviderError as e:
                self.log("[provider] used=%s model=%s status=error (%s) -> bascule" % (pid, p["model"], S.redact_secrets(str(e), self.cfg)))
                last_err = e
                continue
        raise NoProviderAvailable("tous les fournisseurs gratuits ont échoué : %s" % (last_err or "inconnu"))
