#!/usr/bin/env python3
"""Plateforme LLM multi-fournisseurs GRATUITS (pérenne, sans dépendance forte).

Le routeur lit UNIQUEMENT config/providers.json (déclaratif). Il :
- auto-détecte les fournisseurs dont la clé est présente et qui sont éligibles (gratuit, sans carte) ;
- construit une chaîne de secours ordonnée par un score APPRIS (qualité/succès) puis par la priorité ;
- essaie plusieurs modèles par fournisseur (ex. Gemini flash-lite -> flash -> …) ;
- bascule sur 429 / erreur / timeout ; s'arrête proprement si aucun quota gratuit ;
- enregistre des métriques par fournisseur (jamais de secret).

Contraintes dures : jamais de fournisseur payant, jamais de carte bancaire, jamais GitHub Models,
jamais de clé OpenAI. allow_paid_usage doit rester false (vérifié en préflight).
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_checks as S
import quota_manager as Q
from providers import adapters

METRICS_FILE = "runs/provider_metrics.json"
SCORES_FILE = "runs/provider_scores.json"


class NoProviderAvailable(Exception):
    """Aucun fournisseur gratuit utilisable (clés absentes, tous en cooldown, ou aucun actif)."""


class ProviderRouter:
    def __init__(self, providers_cfg, policies, logger=None, state_dir=None):
        self.cfg = providers_cfg
        self.policies = policies
        self.log = logger or (lambda m: print(m))
        self.state_dir = state_dir or os.path.join(S.AGENT_WORK)
        self.log("[router] init: AXA_FORCE_PROVIDER present: %s | AXA_FORCE_MODEL present: %s" % (
            "true" if os.environ.get("AXA_FORCE_PROVIDER") else "false",
            "true" if os.environ.get("AXA_FORCE_MODEL") else "false"))

    # ------------------------------------------------------------------ éligibilité & clés
    def _key_for(self, p):
        env = p.get("api_key_env")
        return os.environ.get(env) if env else None

    def _account_for(self, p):
        env = p.get("account_id_env")
        return os.environ.get(env) if env else None

    def _eligible(self, p):
        """Un fournisseur n'est ÉLIGIBLE que s'il est gratuit, sans carte, actif, avec clé présente."""
        if not p.get("active", p.get("enabled")):
            return False
        if (not p.get("free_tier", False)) or p.get("requires_paid", False) or p.get("requires_card", False):
            return False
        if not adapters.STYLES.get(p.get("style")):
            return False
        if not self._key_for(p):
            return False
        if p.get("style") == "cloudflare" and not self._account_for(p):
            return False
        return True

    # ------------------------------------------------------------------ scores appris
    def _scores(self):
        return S.load_json(os.path.join(self.state_dir, SCORES_FILE), default={}).get("providers", {})

    def _rank_key(self, pid, p, scores):
        s = scores.get(pid, {})
        quality = float(s.get("quality", 50.0))          # 0..100, défaut neutre
        succ = int(s.get("success", 0)); err = int(s.get("error", 0))
        rate = (succ + 1) / (succ + err + 2)             # taux de succès lissé
        # score global : qualité apprise (0.7) + fiabilité (0.3) ; plus haut = meilleur
        composite = quality * 0.7 + rate * 100 * 0.3
        return (-composite, int(p.get("priority", 99)), pid)

    # ------------------------------------------------------------------ détection & ordre
    def autodetect(self):
        """Détecte les fournisseurs (clé présente, éligible, cooldown) et l'ordre de la chaîne de secours."""
        scores = self._scores()
        report = []
        for pid, p in self.cfg.get("providers", {}).items():
            report.append({
                "provider": pid, "active": bool(p.get("active", p.get("enabled"))),
                "key_present": bool(self._key_for(p)),
                "eligible": self._eligible(p), "in_cooldown": Q.provider_in_cooldown(pid),
                "priority": p.get("priority", 99), "models": p.get("models") or ([p.get("model")] if p.get("model") else []),
                "quality_score": scores.get(pid, {}).get("quality", 50.0),
            })
        return report

    def forced_provider(self):
        """Fournisseur imposé par le chef d'orchestre (AXA_FORCE_PROVIDER) : PAS de second routage."""
        return os.environ.get("AXA_FORCE_PROVIDER") or None

    def available(self):
        """Chaîne de secours : fournisseurs éligibles, hors cooldown, ordonnés par score appris puis priorité.

        Si un fournisseur est IMPOSÉ (AXA_FORCE_PROVIDER), le routeur ne fait PAS de second routage : il
        retourne uniquement ce fournisseur (s'il est éligible), en IGNORANT le cooldown local — car
        l'orchestrateur, autoritaire, l'a déjà jugé disponible via son propre registre d'état."""
        forced = self.forced_provider()
        if forced:
            p = self.cfg.get("providers", {}).get(forced)
            elig = bool(p and self._eligible(p))
            self.log("[router] available(): forcé=%s présent_config=%s éligible=%s -> %s" % (
                forced, bool(p), elig, [forced] if elig else []))
            if p and not elig:
                # pourquoi non éligible ? (jamais de clé affichée)
                self.log("[router] %s non éligible : active=%s free=%s key=%s style=%s" % (
                    forced, p.get("active", p.get("enabled")), p.get("free_tier"),
                    bool(self._key_for(p)), p.get("style")))
            return [forced] if elig else []
        scores = self._scores()
        elig = [(pid, p) for pid, p in self.cfg.get("providers", {}).items()
                if self._eligible(p) and not Q.provider_in_cooldown(pid)]
        elig.sort(key=lambda t: self._rank_key(t[0], t[1], scores))
        return [pid for pid, _ in elig]

    # ------------------------------------------------------------------ métriques (jamais de secret)
    def _record(self, pid, model, outcome, tin, tout, dt, dry_run):
        if dry_run:
            return
        path = os.path.join(self.state_dir, METRICS_FILE)
        data = S.load_json(path, default={"providers": {}})
        d = data["providers"].setdefault(pid, {"calls": 0, "success": 0, "error": 0, "timeout": 0,
                                               "tokens_in": 0, "tokens_out": 0, "total_time_s": 0.0, "models": {}})
        d["calls"] += 1
        d[outcome] = d.get(outcome, 0) + 1
        d["tokens_in"] += int(tin or 0); d["tokens_out"] += int(tout or 0)
        d["total_time_s"] = round(d.get("total_time_s", 0.0) + dt, 3)
        if model:
            d["models"][model] = d["models"].get(model, 0) + 1
        data["updated_at"] = S.now_iso()
        S.write_json(path, data)
        # met à jour le score de fiabilité (succès/erreur) — la QUALITÉ vient du benchmark
        spath = os.path.join(self.state_dir, SCORES_FILE)
        sc = S.load_json(spath, default={"providers": {}})
        s = sc["providers"].setdefault(pid, {"quality": 50.0, "success": 0, "error": 0})
        if outcome == "success":
            s["success"] += 1
        elif outcome in ("error", "timeout"):
            s["error"] += 1
        sc["updated_at"] = S.now_iso()
        S.write_json(spath, sc)

    # ------------------------------------------------------------------ appel
    def chat(self, messages, max_tokens, budget, dry_run=False):
        est_in = Q.estimate_tokens("\n".join(m.get("content", "") for m in messages))
        budget.before_call(est_in)  # peut lever QuotaExhausted

        providers = self.available()
        if not providers:
            raise NoProviderAvailable("aucun fournisseur gratuit disponible (clés absentes / cooldown / inactifs)")

        timeout = self.policies.get("limits", {}).get("http_timeout_seconds", 20)
        last_err = None
        for pid in providers:
            p = self.cfg["providers"][pid]
            style = adapters.STYLES[p["style"]]
            key = self._key_for(p)
            account_id = self._account_for(p)
            models = p.get("models") or ([p.get("model")] if p.get("model") else [])
            fmodel = os.environ.get("AXA_FORCE_MODEL")
            if self.forced_provider() == pid and fmodel:
                models = [fmodel]   # modèle imposé par l'orchestrateur : un seul essai, pas de second routage
            for model in models:
                if pid == "openrouter" and ":free" not in model:
                    continue  # OpenRouter : jamais un modèle payant, même en dernier recours
                pcfg = dict(p); pcfg["model"] = model
                self.log("[router] appel adaptateur -> provider=%s model=%s (clé présente=%s)" % (
                    pid, model, bool(key)))
                t0 = time.time()
                try:
                    text, tin, tout = style(pcfg, key, account_id, messages, max_tokens, timeout)
                    dt = time.time() - t0
                    tin = tin or est_in; tout = tout or Q.estimate_tokens(text)
                    budget.record(tin, tout)
                    self._record(pid, model, "success", tin, tout, dt, dry_run)
                    self.log("[provider] used=%s model=%s tokens_in~%d tokens_out~%d time=%.2fs status=ok" % (pid, model, tin, tout, dt))
                    return {"text": text, "provider": pid, "model": model, "tokens_in": tin, "tokens_out": tout, "time_s": round(dt, 3)}
                except adapters.RateLimited as e:
                    dt = time.time() - t0
                    self._record(pid, model, "error", 0, 0, dt, dry_run)
                    self.log("[provider] used=%s model=%s status=rate_limited (%s) -> cooldown+bascule" % (pid, model, e))
                    Q.set_cooldown(pid, seconds=6 * 3600, dry_run=dry_run)
                    last_err = e
                    break  # 429 : inutile d'essayer les autres modèles de ce fournisseur
                except adapters.ProviderError as e:
                    dt = time.time() - t0
                    outcome = "timeout" if "timeout" in str(e).lower() or "réseau" in str(e).lower() else "error"
                    self._record(pid, model, outcome, 0, 0, dt, dry_run)
                    self.log("[provider] used=%s model=%s status=%s (%s) -> modèle/fournisseur suivant" % (
                        pid, model, outcome, S.redact_secrets(str(e), self.cfg)))
                    last_err = e
                    continue
        raise NoProviderAvailable("tous les fournisseurs gratuits ont échoué : %s" % (last_err or "inconnu"))


# ------------------------------------------------------------------ CLI : rapport de détection / métriques
def _table():
    cfg = S.load_providers_config(); pol = S.load_policies()
    r = ProviderRouter(cfg, pol)
    print("== Auto-détection des fournisseurs (chaîne de secours) ==")
    for row in r.autodetect():
        print("  %-12s active=%s clé=%s éligible=%s cooldown=%s prio=%s qualité=%.0f modèles=%s" % (
            row["provider"], row["active"], row["key_present"], row["eligible"], row["in_cooldown"],
            row["priority"], float(row["quality_score"]), ", ".join(row["models"][:2])))
    print("  Ordre effectif :", " -> ".join(r.available()) or "(aucun — configurez une clé)")
    m = S.load_json(os.path.join(S.AGENT_WORK, METRICS_FILE), default={"providers": {}})
    if m["providers"]:
        print("\n== Métriques par fournisseur ==")
        for pid, d in m["providers"].items():
            avg = (d["total_time_s"] / d["calls"]) if d.get("calls") else 0
            print("  %-12s appels=%d succès=%d erreurs=%d timeouts=%d tok_in=%d tok_out=%d temps_moy=%.2fs" % (
                pid, d.get("calls", 0), d.get("success", 0), d.get("error", 0), d.get("timeout", 0),
                d.get("tokens_in", 0), d.get("tokens_out", 0), avg))


if __name__ == "__main__":
    _table()
