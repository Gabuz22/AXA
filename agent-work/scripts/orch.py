#!/usr/bin/env python3
"""Chef d'orchestre — bibliothèque centrale (file de tâches, registre de fournisseurs, routage).

Réutilise l'existant (provider_router, quota_manager, coordinateur, agents, garde-fous) sans le
dupliquer. Un AGENT = une mission ; un FOURNISSEUR/MODÈLE = un moteur interchangeable : aucun agent
n'est lié à un fournisseur. Tout l'état est persistant sous agent-work/orchestrator/ (base injectable
pour les tests). Zéro coût : allow_paid_usage doit rester false, max_cost = 0, jamais de fallback payant.
"""
import os, json, time, datetime, hashlib
import safety_checks as S

# ------------------------------------------------------------------ statuts & états
TASK_STATUSES = {"ready", "running", "waiting_provider", "waiting_reset", "waiting_dependency",
                 "completed", "no_work", "failed_retryable", "failed_terminal", "blocked_human_review"}
PROVIDER_STATES = {"available", "cooldown", "quota_exhausted", "auth_error",
                   "model_unavailable", "provider_unavailable", "disabled"}

COOLDOWN_SECONDS = {"rate_minute": 90, "provider_unavailable": 600, "content_error": 0}
AUTH_COOLDOWN_SECONDS = 24 * 3600         # 401/403 : ne pas re-tenter en boucle ; intervention humaine
STALE_RUNNING_SECONDS = 30 * 60           # une tâche 'running' plus vieille = crash -> requeue


def detect_keys(providers_cfg):
    """Détection RÉELLE des clés depuis l'environnement COURANT (recalculée à chaque cycle).
    Retourne {provider: bool}. Ne lit ni ne révèle aucune valeur."""
    out = {}
    for pid, p in (providers_cfg or {}).items():
        present = bool(os.environ.get(p.get("api_key_env", "")))
        if p.get("style") == "cloudflare":
            present = present and bool(os.environ.get(p.get("account_id_env", "")))
        out[pid] = present
    return out


def idempotency_key(cycle_id, task_id, agent_type):
    """Clé d'idempotence : une tâche donnée n'est exécutée qu'une fois par cycle."""
    return "%s|%s|%s" % (cycle_id, task_id, agent_type)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt=None):
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(iso):
    try:
        return datetime.datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except Exception:
        return None


def _next_utc_midnight():
    n = _now()
    return (n + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


# ------------------------------------------------------------------ classification d'erreurs
def classify_error(code, msg=""):
    """Différencie strictement les causes. Retourne (categorie, provider_state, cooldown_s, needs_human)."""
    m = (msg or "").lower()
    if code in (401, 403):
        return "auth_error", "auth_error", AUTH_COOLDOWN_SECONDS, True
    if code == 404:
        return "model_unavailable", "model_unavailable", 0, False
    if code == 429:
        if any(w in m for w in ("day", "daily", "jour", "quota")):
            return "quota_daily", "quota_exhausted", None, False       # None => reset au prochain minuit UTC
        return "rate_minute", "cooldown", COOLDOWN_SECONDS["rate_minute"], False
    if code == 0 or code >= 500:
        return "provider_unavailable", "provider_unavailable", COOLDOWN_SECONDS["provider_unavailable"], False
    return "content_error", None, 0, False   # pas un problème fournisseur (ne pas mettre en repos)


# ------------------------------------------------------------------ registre de fournisseurs
class ProviderRegistry:
    def __init__(self, base_dir):
        self.path = os.path.join(base_dir, "provider_state.json")
        self.data = S.load_json(self.path, default={"providers": {}, "updated_at": None})

    def _p(self, provider):
        return self.data["providers"].setdefault(provider, {
            "state": "available", "key_detected": None, "last_check": None, "next_available_at": None,
            "calls_used_est": 0, "tokens_in": 0, "tokens_out": 0, "latency_avg_s": 0.0, "success": 0,
            "errors": {"401": 0, "403": 0, "404": 0, "429": 0, "5xx": 0}, "success_rate": 1.0,
            "quality": 50.0, "disabled_models": [], "needs_human": False, "last_cause": None,
            "quota_source": "estimation_prudente"})

    def reactivate_expired(self):
        """Repli/reset : un fournisseur en repos dont next_available_at est passé redevient available."""
        for pid, p in self.data["providers"].items():
            if p.get("state") in ("cooldown", "quota_exhausted", "provider_unavailable"):
                na = _parse(p.get("next_available_at"))
                if na and _now() >= na:
                    p["state"] = "available"; p["next_available_at"] = None; p["last_cause"] = "reset"
        return self

    def set_key_detected(self, provider, present):
        self._p(provider)["key_detected"] = bool(present)

    def is_available(self, provider):
        p = self._p(provider)
        if p["state"] in ("auth_error", "disabled"):
            return False
        na = _parse(p.get("next_available_at"))
        if p["state"] != "available" and na and _now() < na:
            return False
        if p["state"] != "available" and (not na):
            return False
        return True

    def model_available(self, provider, model):
        return self.is_available(provider) and model not in self._p(provider).get("disabled_models", [])

    def record_success(self, provider, model, tin, tout, latency):
        p = self._p(provider)
        p["state"] = "available"; p["next_available_at"] = None; p["last_cause"] = "ok"
        p["success"] += 1; p["calls_used_est"] += 1
        p["tokens_in"] += int(tin or 0); p["tokens_out"] += int(tout or 0)
        n = p["success"] + sum(p["errors"].values())
        p["latency_avg_s"] = round((p["latency_avg_s"] * (n - 1) + latency) / max(1, n), 3)
        p["success_rate"] = round(p["success"] / max(1, n), 3)
        p["last_check"] = _iso()

    def record_error(self, provider, model, code, msg, latency):
        cat, state, cooldown, needs_human = classify_error(code, msg)
        p = self._p(provider)
        key = "5xx" if (code and code >= 500) else str(code)
        if key in p["errors"]:
            p["errors"][key] += 1
        p["calls_used_est"] += 1
        n = p["success"] + sum(p["errors"].values())
        p["latency_avg_s"] = round((p["latency_avg_s"] * (n - 1) + latency) / max(1, n), 3)
        p["success_rate"] = round(p["success"] / max(1, n), 3)
        p["last_check"] = _iso(); p["last_cause"] = cat
        if cat == "model_unavailable":
            if model and model not in p["disabled_models"]:
                p["disabled_models"].append(model)     # désactive CE modèle, pas le fournisseur
            return cat
        if state:                                       # met le fournisseur au repos
            p["state"] = state
            p["needs_human"] = p.get("needs_human") or needs_human
            if cooldown is None:                        # quota journalier -> reset au minuit UTC
                p["next_available_at"] = _iso(_next_utc_midnight()); p["quota_source"] = "estimation_reset_minuit_utc"
            elif cooldown > 0:
                p["next_available_at"] = _iso(_now() + datetime.timedelta(seconds=cooldown))
        return cat

    def disable_model(self, provider, model):
        """Reflète un modèle retiré (404) dans provider_state.json sans mettre le fournisseur en erreur."""
        p = self._p(provider)
        if model and model not in p["disabled_models"]:
            p["disabled_models"].append(model)
            p.setdefault("disabled_models_meta", {})[model] = {"cause": "model_unavailable", "at": _iso()}

    def snapshot(self):
        out = []
        for pid, p in self.data["providers"].items():
            out.append({"provider": pid, "state": p["state"], "next_available_at": p.get("next_available_at"),
                        "success_rate": p.get("success_rate"), "quality": p.get("quality"),
                        "needs_human": p.get("needs_human"), "calls_used_est": p.get("calls_used_est")})
        return out

    def save(self, dry_run=False):
        if dry_run:
            return
        self.data["updated_at"] = _iso()
        S.write_json(self.path, self.data)


# ------------------------------------------------------------------ file de tâches
def task_fingerprint(t):
    key = "|".join(str(t.get(k, "")) for k in ("agent_type", "contract", "document", "pages", "category"))
    return "t_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class TaskQueue:
    def __init__(self, base_dir):
        self.path = os.path.join(base_dir, "task_queue.json")
        self.data = S.load_json(self.path, default={"version": "1.0.0", "tasks": []})

    def _by_id(self, tid):
        return next((t for t in self.data["tasks"] if t.get("task_id") == tid), None)

    def add(self, agent_type, **fields):
        t = {
            "task_id": None, "agent_type": agent_type, "status": "ready", "priority": fields.get("priority", 3),
            "created_at": _iso(), "next_attempt_at": _iso(), "estimated_input_tokens": fields.get("estimated_input_tokens", 2000),
            "estimated_output_tokens": fields.get("estimated_output_tokens", 600),
            "required_capabilities": fields.get("required_capabilities", []),
            "compatible_providers": fields.get("compatible_providers", []), "compatible_models": fields.get("compatible_models", []),
            "contract": fields.get("contract"), "document": fields.get("document"), "pages": fields.get("pages"),
            "category": fields.get("category"), "attempts": 0, "max_attempts": fields.get("max_attempts", 4),
            "last_provider": None, "last_model": None, "last_error": None, "dependencies": fields.get("dependencies", []),
            "source_gap_id": fields.get("source_gap_id"), "human_validation_required": fields.get("human_validation_required", True),
            "owner_cycle": None,
        }
        t["task_id"] = task_fingerprint(t)
        if self._by_id(t["task_id"]):        # anti-doublon strict
            return self._by_id(t["task_id"]), False
        self.data["tasks"].append(t)
        return t, True

    def recover_stale(self):
        """Reprise après crash : une tâche 'running' trop ancienne repasse 'ready' (sans doublon)."""
        for t in self.data["tasks"]:
            if t.get("status") == "running":
                started = _parse(t.get("running_since"))
                if (not started) or (_now() - started).total_seconds() > STALE_RUNNING_SECONDS:
                    t["status"] = "ready"; t["owner_cycle"] = None
        return self

    def ready_tasks(self):
        done = {t["task_id"] for t in self.data["tasks"] if t.get("status") == "completed"}
        out = []
        for t in self.data["tasks"]:
            if t.get("status") not in ("ready", "waiting_provider", "waiting_reset"):
                continue
            if _parse(t.get("next_attempt_at")) and _now() < _parse(t["next_attempt_at"]):
                continue
            if any(dep not in done for dep in (t.get("dependencies") or [])):
                t["status"] = "waiting_dependency"; continue
            out.append(t)
        out.sort(key=lambda t: (-int(t.get("priority", 0)), t.get("created_at", "")))
        return out

    def claim(self, task, cycle_id):
        """Empêche l'exécution simultanée : un seul cycle peut passer une tâche en 'running'."""
        if task.get("status") == "running" and task.get("owner_cycle") not in (None, cycle_id):
            return False
        task["status"] = "running"; task["owner_cycle"] = cycle_id; task["running_since"] = _iso()
        task["attempts"] = int(task.get("attempts", 0)) + 1
        return True

    def finish(self, task, status, provider=None, model=None, error=None, retry_delay_s=0):
        task["status"] = status; task["owner_cycle"] = None
        task["last_provider"] = provider or task.get("last_provider")
        task["last_model"] = model or task.get("last_model")
        if error:
            task["last_error"] = str(error)[:200]
        if status == "failed_retryable":
            if int(task.get("attempts", 0)) >= int(task.get("max_attempts", 4)):
                task["status"] = "failed_terminal"
            else:
                task["next_attempt_at"] = _iso(_now() + datetime.timedelta(seconds=max(1, retry_delay_s)))
                task["status"] = "waiting_reset" if retry_delay_s > 300 else "ready"

    def apply_outcome(self, task, outcome, provider=None, model=None, cause=None):
        """Traduit un RÉSULTAT MÉTIER (jamais un simple exit code) en statut de tâche.
        Règle stricte : 'completed' UNIQUEMENT si la zone a été réellement analysée par le LLM sans
        donnée utile (analyzed_no_data). Une proposition écrite => revue humaine. Un no_work causé par
        un fournisseur/modèle indisponible, un quota ou l'absence d'appel => réessai, jamais 'completed'."""
        task["owner_cycle"] = None
        task["last_provider"] = provider or task.get("last_provider")
        task["last_model"] = model or task.get("last_model")
        if cause:
            task["last_error"] = str(cause)[:200]
        task.pop("completion_reason", None)
        if outcome == "produced":
            task["status"] = "blocked_human_review"          # travail réel -> validation humaine (jamais 'completed' silencieux)
        elif outcome == "analyzed_no_data":
            task["status"] = "completed"; task["completion_reason"] = "analyzed_no_data"
        elif outcome == "auth_error":
            task["status"] = "failed_terminal"               # 401/403 -> intervention humaine, pas de boucle
        elif outcome == "quota":
            if int(task.get("attempts", 0)) >= int(task.get("max_attempts", 4)):
                task["status"] = "failed_terminal"
            else:
                task["status"] = "waiting_reset"
                task["next_attempt_at"] = _iso(_now() + datetime.timedelta(hours=6))
        else:                                                 # waiting_provider / no_work / inconnu -> JAMAIS completed
            task["status"] = "waiting_provider"
            task["next_attempt_at"] = _iso(_now() + datetime.timedelta(minutes=30))
        return task["status"]

    def counts(self):
        c = {}
        for t in self.data["tasks"]:
            c[t["status"]] = c.get(t["status"], 0) + 1
        return c

    def save(self, dry_run=False):
        if dry_run:
            return
        S.write_json(self.path, self.data)


# ------------------------------------------------------------------ migration d'état (idempotente)
def _valid_extraction_index(policies=None):
    """Ensemble {(contract_slug, categorie)} des propositions d'extraction VALIDES (pending + reviewed).
    Une confiance > 0.95 (ancienne version) est INVALIDE => exclue : elle ne compte pas comme travail réel."""
    import glob as _glob
    try:
        import validate_proposal as VP
    except Exception:
        VP = None
    idx = set()
    for sub in ("pending", "reviewed"):
        for f in _glob.glob(os.path.join(S.AGENT_WORK, "extraction", sub, "*.json")):
            try:
                p = S.load_json(f)
            except Exception:
                continue
            if p.get("agent_id") != "extraction-llm":
                continue
            if VP is not None:
                ok, _errs = VP.validate(p, policies)
                if not ok:
                    continue
            slug = (p.get("target") or {}).get("contract")
            cat = ((p.get("proposed_change") or {}).get("payload") or {}).get("categorie")
            if slug and cat:
                idx.add((slug, cat))
    return idx


def unstick_burned_tasks(queue, policies=None):
    """Migration idempotente. Réactive UNIQUEMENT les tâches 'completed' BRÛLÉES : celles qui n'ont
    jamais produit de proposition VALIDE et ne portent pas completion_reason='analyzed_no_data'.
    Ne rouvre JAMAIS une tâche réellement terminée. Rejouable : une tâche déjà réactivée est 'ready'
    (plus 'completed') et n'est donc plus concernée. Retourne la liste des task_id réactivés."""
    idx = _valid_extraction_index(policies)
    reopened = []
    for t in queue.data["tasks"]:
        if t.get("status") != "completed":
            continue
        if t.get("completion_reason") == "analyzed_no_data":
            continue                                          # réellement analysée sans donnée -> ne pas rouvrir
        slug = S.sanitize_filename(t.get("contract") or "").lower()
        if (slug, t.get("category")) in idx:
            continue                                          # proposition valide liée -> réellement terminée
        t["status"] = "ready"; t["attempts"] = 0; t["owner_cycle"] = None
        t["next_attempt_at"] = _iso()
        t["reopened_reason"] = "completed sans proposition valide ni appel LLM utile (migration no_work)"
        t["reopened_at"] = _iso()
        reopened.append(t.get("task_id"))
    return reopened


# ------------------------------------------------------------------ politique zéro-coût
class CostPolicy:
    def __init__(self, policies, per_provider_cycle_cap=3, safety_margin=1):
        if policies.get("allow_paid_usage", False):
            raise S.SafetyError("allow_paid_usage=true interdit (zéro coût).")
        self.cap = per_provider_cycle_cap
        self.margin = safety_margin
        self.used = {}

    def can_call(self, provider):
        # marge de sécurité : on s'arrête AVANT le plafond estimé (cap - margin appels max).
        return self.used.get(provider, 0) < max(1, self.cap - self.margin)

    def record(self, provider):
        self.used[provider] = self.used.get(provider, 0) + 1


# ------------------------------------------------------------------ routage explicable
def _reasoning_ok(prov_cfg, caps, ranks):
    need = ranks.get(caps.get("reasoning_min", "faible"), 1)
    have = ranks.get(prov_cfg.get("reasoning", "moyen"), 2)
    return have >= need


def _pick_model(pid, prov_cfg, caps, registry):
    models = prov_cfg.get("models") or ([prov_cfg.get("model")] if prov_cfg.get("model") else [])
    compat = set(caps.get("compatible_models") or [])
    for m in models:
        if compat and m not in compat:
            continue
        if pid == "openrouter" and ":free" not in m:      # OpenRouter : jamais un modèle payant
            continue
        if registry.model_available(pid, m):
            return m
    return None


def choose_engine(task, agent_caps, providers_cfg, registry, scores, ranks,
                  exclude_providers=None, explore_jitter=0.0):
    """Retourne une décision de routage EXPLICABLE ou None. Ne choisit jamais un modèle « juste parce
    qu'il est disponible » : capacités, qualité historique, coût (0), latence, priorité, diversification."""
    exclude = set(exclude_providers or [])
    compat_prov = set(agent_caps.get("compatible_providers") or list(providers_cfg.keys()))
    candidates, rejected = [], []
    for pid in compat_prov:
        p = providers_cfg.get(pid)
        if not p:
            rejected.append((pid, "inconnu")); continue
        if pid in exclude:
            rejected.append((pid, "exclu (diversification)")); continue
        if not p.get("active", p.get("enabled")) or not p.get("free_tier") or p.get("requires_paid") or p.get("requires_card"):
            rejected.append((pid, "non gratuit/inactif")); continue
        if registry._p(pid).get("key_detected") is False:
            rejected.append((pid, "clé absente")); continue
        if agent_caps.get("json_strict") and not p.get("json_capable", True):
            rejected.append((pid, "pas JSON strict")); continue
        if not _reasoning_ok(p, agent_caps, ranks):
            rejected.append((pid, "raisonnement insuffisant")); continue
        if not registry.is_available(pid):
            rejected.append((pid, "au repos (%s)" % registry._p(pid).get("state"))); continue
        model = _pick_model(pid, p, agent_caps, registry)
        if not model:
            rejected.append((pid, "aucun modèle compatible/gratuit dispo")); continue
        s = scores.get(pid, {})
        quality = float(s.get("quality", 50.0))
        samples = int(s.get("samples", 0))
        rel = float(registry._p(pid).get("success_rate", 1.0))
        lat = float(registry._p(pid).get("latency_avg_s", 1.0)) or 1.0
        prio = int(p.get("priority", 99))
        # Exploration contrôlée tant que peu d'échantillons : on n'écrase pas la priorité statique.
        learned = quality if samples >= 3 else 50.0
        score = learned * 0.5 + rel * 100 * 0.2 + (1.0 / lat) * 5 * 0.15 + (100 - prio) * 0.15 + explore_jitter
        if learned < float(agent_caps.get("min_quality_history", 0)) and samples >= 3:
            rejected.append((pid, "qualité historique < seuil")); continue
        candidates.append({"provider": pid, "model": model, "score": round(score, 2),
                           "quality": learned, "priority": prio, "reliability": rel, "latency": lat})
    if not candidates:
        return None, {"reason": "aucun moteur gratuit compatible disponible", "rejected": rejected}
    candidates.sort(key=lambda c: -c["score"])
    best = candidates[0]
    decision = {
        "task_id": task.get("task_id"), "agent": task.get("agent_type"),
        "provider": best["provider"], "model": best["model"],
        "alternatives": [{"provider": c["provider"], "model": c["model"], "score": c["score"]} for c in candidates[1:]],
        "rejected": rejected,
        "reason": "meilleur score gratuit (qualité=%.0f, fiabilité=%.2f, prio=%d, latence=%.2fs)" % (
            best["quality"], best["reliability"], best["priority"], best["latency"]),
        "estimated_cost": 0, "next_on_fail": "bascule fournisseur suivant ou waiting_reset",
    }
    return decision, {"candidates": candidates}


# ------------------------------------------------------------------ verrou de cycle
def acquire_cycle_lock(base_dir, cycle_id, ttl_s=1800, dry_run=False):
    """Verrou de concurrence : refuse un second cycle tant qu'un verrou frais existe."""
    path = os.path.join(base_dir, "locks", "cycle.lock")
    existing = S.load_json(path, default={}) if os.path.isfile(path) else {}
    if existing:
        started = _parse(existing.get("started_at"))
        if started and (_now() - started).total_seconds() < ttl_s:
            return False, existing.get("cycle_id")
    if not dry_run:
        S.write_json(path, {"cycle_id": cycle_id, "started_at": _iso(), "ttl_s": ttl_s})
    return True, cycle_id


def release_cycle_lock(base_dir, dry_run=False):
    path = os.path.join(base_dir, "locks", "cycle.lock")
    if not dry_run and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
