#!/usr/bin/env python3
"""Serveur HTTP local en lecture seule pour Gabriel Virtuel.

Structure 00-01 / 00-02 : sert la VRAIE racine (parent) quand
00-01_ChoixInterface.html y est present.

Modes :
  python start_local_server.py            -> LOCAL (127.0.0.1)
  python start_local_server.py --lan      -> LAN   (0.0.0.0)
  options : --port 8787  --no-browser  --open {choix,cockpit}

Presence reseau (en MEMOIRE seulement, aucune ecriture disque) :
  GET /__gv/ping?role=...&id=...  -> enregistre {ip, role, ua}
  GET /__gv/devices               -> liste des appareils vus < 60 s

URL canonique permanente (additif) :
  GET /go  /app  /latest  /patrimoine  /cockpit/latest  -> 302 vers la DERNIERE version.

Sauvegarde locale de la donnee vivante (additif, ECRITURE LIMITEE) :
  POST /__gv/backup  (corps JSON)  -> ecrit UNIQUEMENT dans backups/local_data/<device>/.
  Aucune autre ecriture disque n'est permise. Les JSON meres ne sont jamais touches.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from urllib.parse import urlsplit, parse_qs


DEFAULT_PORT = 8787
SCRIPT_DIR = Path(__file__).resolve().parent
COCKPIT_DIR = SCRIPT_DIR / "cockpit"

_PARENT = SCRIPT_DIR.parent
if (_PARENT / "00-01_ChoixInterface.html").is_file():
    SERVE_ROOT = _PARENT
    PREFIX = "/" + SCRIPT_DIR.name
    CHOIX_PATH = "/00-01_ChoixInterface.html"
else:
    SERVE_ROOT = SCRIPT_DIR
    PREFIX = ""
    CHOIX_PATH = ""

VERSION_PATTERN = re.compile(r"^index_gabriel_virtuel_v(?P<version>\d+(?:\.\d+)+)\.html$")

# Registre de presence : cle (ip, cid) -> {role, ua, ip, ts}. En memoire uniquement.
PRESENCE: dict = {}
PRESENCE_TTL = 60.0

# --- Sauvegarde locale (ecriture limitee a ce dossier) ---
BACKUP_BASE = SCRIPT_DIR / "backups" / "local_data"
ALLOWED_DEVICES = {"persoSamsung", "persoPc", "proIphone", "proIpad", "unknown"}
BACKUP_MAX_BYTES = 30 * 1024 * 1024  # 30 Mo de garde-fou

# --- Memoire centrale (boite d'entree append-only ; JAMAIS les meres) ---
LIVE_INBOX = SCRIPT_DIR / "updates" / "live_inbox"
ALLOWED_LIVE_TYPES = {"journal", "reflexions", "decisions", "reves", "notes",
                      "patrimoine_transactions", "relations", "messages", "audit"}
LIVE_MAX_BYTES = 2 * 1024 * 1024  # 2 Mo par entree
LIVE_SEEN: set = set()  # ids deja recus (anti-doublon en memoire)


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def detect_latest_cockpit() -> tuple[str, Path]:
    candidates = []
    if COCKPIT_DIR.is_dir():
        for cockpit_path in COCKPIT_DIR.iterdir():
            match = VERSION_PATTERN.match(cockpit_path.name)
            if match and cockpit_path.is_file():
                version = match.group("version")
                candidates.append((version_key(version), version, cockpit_path))
    if not candidates:
        raise RuntimeError(f"Aucun cockpit versionne trouve dans {COCKPIT_DIR}")
    _, version, cockpit_path = max(candidates, key=lambda item: item[0])
    return version, cockpit_path


def lan_ip() -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        probe.close()


BIND_HOST = "127.0.0.1"  # renseigne dans main()
ACTIVE_PORT = DEFAULT_PORT  # renseigne dans main()


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except Exception:
        return ""


def classify_iface(iface: str, ip: str) -> str:
    """Classe une IP/interface : hotspot, wifi, mobile(CGNAT), prive, loopback, autre."""
    name = (iface or "").lower()
    octs = ip.split(".")
    a = int(octs[0]) if octs and octs[0].isdigit() else -1
    b = int(octs[1]) if len(octs) > 1 and octs[1].isdigit() else -1
    last = octs[3] if len(octs) > 3 else ""
    if ip.startswith("127.") or ip == "::1":
        return "loopback"
    is_priv = (a == 192 and b == 168) or (a == 10) or (a == 172 and 16 <= b <= 31)
    is_cgnat = (a == 100 and 64 <= b <= 127)
    hotspot_iface = any(k in name for k in ("ap", "swlan", "softap", "wlan1", "rndis", "usb", "tether", "bridge", "bt-pan"))
    mobile_iface = any(k in name for k in ("rmnet", "ccmni", "radio", "pdp", "wwan", "rmnet_data"))
    if is_priv and (hotspot_iface or last == "1"):
        return "hotspot"
    if is_priv and ("wlan" in name or "wifi" in name or name.startswith("eth")):
        return "wifi"
    if is_priv:
        return "wifi" if "wlan" in name else "prive"
    if is_cgnat or mobile_iface:
        return "mobile"
    return "autre"


def enumerate_interfaces():
    """Liste [{iface, ip, kind}] via 'ip -o -4 addr' puis repli 'ifconfig'."""
    out = []
    txt = _run(["ip", "-o", "-4", "addr", "show"])
    if txt:
        for line in txt.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[2] == "inet":
                iface = parts[1]
                ip = parts[3].split("/")[0]
                out.append({"iface": iface, "ip": ip, "kind": classify_iface(iface, ip)})
    if not out:
        txt = _run(["ifconfig"])
        cur = "?"
        for line in txt.splitlines():
            if line and not line.startswith((" ", "\t")):
                cur = line.split()[0].rstrip(":")
            m = re.search(r"inet (?:addr:)?(\d+\.\d+\.\d+\.\d+)", line)
            if m:
                ip = m.group(1)
                out.append({"iface": cur, "ip": ip, "kind": classify_iface(cur, ip)})
    return out


def default_gateway():
    txt = _run(["ip", "route", "show", "default"])
    m = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", txt)
    return m.group(1) if m else ""


def netinfo():
    ifs = enumerate_interfaces()
    def pick(kind):
        for x in ifs:
            if x["kind"] == kind:
                return x["ip"]
        return ""
    hotspot = pick("hotspot")
    wifi = pick("wifi") or pick("prive")
    mobile = pick("mobile")
    recommended = hotspot or wifi or ""
    return {
        "bind_host": BIND_HOST,
        "lan_active": BIND_HOST == "0.0.0.0",
        "port": None,
        "version": ACTIVE_VERSION,
        "interfaces": ifs,
        "gateway": default_gateway(),
        "hotspot_ip": hotspot,
        "wifi_ip": wifi,
        "mobile_ip": mobile,
        "recommended_lan_ip": recommended,
    }


def assert_port_available(port: int) -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(0.4)
    try:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(
                f"Le port {port} est deja utilise. Ferme l'ancien serveur "
                "avant de relancer (STOP_GABRIEL_WINDOWS.bat ou ferme la fenetre)."
            )
    finally:
        probe.close()


ACTIVE_VERSION, ACTIVE_COCKPIT = detect_latest_cockpit()
ACTIVE_PATH = f"{PREFIX}/cockpit/{ACTIVE_COCKPIT.name}"
ROOT_REDIRECT = CHOIX_PATH or ACTIVE_PATH


def sync_latest_pointer() -> str:
    """Maintient cockpit/index_gabriel_virtuel_latest.html identique a la
    derniere version detectee. Empeche le pointeur 'latest' (utilise par
    index.html et 00-01_ChoixInterface.html) de rester fige sur une ancienne
    version. Copie seulement, jamais de suppression. Tolerant aux erreurs."""
    try:
        import shutil
        import hashlib as _hl
        pointer = COCKPIT_DIR / "index_gabriel_virtuel_latest.html"
        src_bytes = ACTIVE_COCKPIT.read_bytes()
        if pointer.exists() and _hl.sha256(pointer.read_bytes()).digest() == _hl.sha256(src_bytes).digest():
            return "deja a jour"
        shutil.copyfile(ACTIVE_COCKPIT, pointer)
        return "resynchronise -> v" + ACTIVE_VERSION
    except Exception as exc:
        return "non synchronise (" + str(exc) + ")"


LATEST_SYNC_STATUS = sync_latest_pointer()

# Adresses canoniques fixes (favoris / raccourcis) -> toujours la derniere version.
CANONICAL_PATHS = {
    "/go", "/app", "/latest", "/patrimoine", "/cockpit/latest",
    PREFIX + "/go", PREFIX + "/app", PREFIX + "/latest",
    PREFIX + "/patrimoine", PREFIX + "/cockpit/latest",
}


def _prune_presence(now: float) -> None:
    for key in list(PRESENCE.keys()):
        if now - PRESENCE[key]["ts"] > PRESENCE_TTL:
            del PRESENCE[key]


def _safe_device(name: str) -> str:
    name = (name or "").strip()
    return name if name in ALLOWED_DEVICES else "unknown"


class ReadOnlyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SERVE_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Gabriel-Virtuel-Version", ACTIVE_VERSION)
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _send_json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_presence(self, parsed) -> bool:
        path = parsed.path
        if path == "/__gv/ping":
            q = parse_qs(parsed.query)
            role = (q.get("role", ["?"])[0] or "?")[:40]
            cid = (q.get("id", ["?"])[0] or "?")[:48]
            ip = self.client_address[0]
            PRESENCE[(ip, cid)] = {
                "role": role,
                "ua": (self.headers.get("User-Agent", "") or "")[:200],
                "ip": ip,
                "ts": time.time(),
            }
            self._send_json({"ok": True, "ip": ip})
            return True
        if path == "/__gv/netinfo":
            info = netinfo(); info["port"] = ACTIVE_PORT
            self._send_json(info)
            return True
        if path == "/__gv/devices":
            now = time.time()
            _prune_presence(now)
            devices = [
                {"ip": v["ip"], "role": v["role"], "ua": v["ua"], "age": int(now - v["ts"])}
                for v in PRESENCE.values()
            ]
            devices.sort(key=lambda d: (d["role"], d["ip"]))
            self._send_json({"devices": devices, "server_ip": lan_ip(), "count": len(devices)})
            return True
        if path == "/__gv/backup_status":
            self._send_json(self._backup_status())
            return True
        if path in ("/__gv/live-status", "/__gv/live-inbox-summary"):
            self._send_json(self._live_summary())
            return True
        return False

    def _live_summary(self) -> dict:
        out = {"base": "updates/live_inbox", "online": True, "types": {}, "total": 0, "recus_session": len(LIVE_SEEN)}
        try:
            for t in sorted(ALLOWED_LIVE_TYPES):
                d = LIVE_INBOX / t
                if d.is_dir():
                    n = 0
                    for f in d.glob("*.jsonl"):
                        try: n += sum(1 for _ in f.open("r", encoding="utf-8"))
                        except Exception: pass
                    if n: out["types"][t] = n; out["total"] += n
        except Exception:
            pass
        return out

    def _handle_live_entry(self) -> None:
        """POST /__gv/live-entry : ajoute UNE entree en JSONL append-only sous updates/live_inbox/<type>/.
        N'ecrit jamais dans les JSON meres. Horodatage + nom de fichier cote serveur (anti-traversee)."""
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        if length <= 0 or length > LIVE_MAX_BYTES:
            self._send_json({"ok": False, "error": "taille invalide"}, 413)
            return
        raw = self.rfile.read(length)
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "json invalide"}, 400)
            return
        if not isinstance(obj, dict):
            self._send_json({"ok": False, "error": "objet attendu"}, 400)
            return
        typ = obj.get("type", "")
        if typ not in ALLOWED_LIVE_TYPES:
            self._send_json({"ok": False, "error": "type non autorise"}, 400)
            return
        device = _safe_device(obj.get("device_id") or obj.get("device"))
        cid = str(obj.get("id") or "")[:80]
        # Anti-doublon : meme id deja recu -> pas de seconde ligne.
        dedup_key = typ + "|" + cid
        if cid and dedup_key in LIVE_SEEN:
            self._send_json({"ok": True, "duplicate": True, "id": cid})
            return
        now = datetime.now()
        rid = cid or (device + "_" + now.strftime("%Y%m%d%H%M%S%f"))
        checksum = hashlib.sha256(json.dumps(obj.get("payload", {}), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        line = {
            "id": rid, "type": typ, "created_at_client": obj.get("created_at_client"),
            "received_at_server": now.isoformat(timespec="seconds"), "device_id": device,
            "origin": (obj.get("origin") or "")[:120], "app_version": (obj.get("app_version") or "")[:20],
            "payload": obj.get("payload", {}), "checksum": checksum,
            "statut": "recu_non_fusionne", "fusion": "jamais automatique",
        }
        try:
            d = LIVE_INBOX / typ
            d.mkdir(parents=True, exist_ok=True)
            fpath = d / (now.strftime("%Y-%m-%d") + ".jsonl")
            with fpath.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
            if cid:
                LIVE_SEEN.add(dedup_key)
            self._send_json({"ok": True, "id": rid, "type": typ, "fichier": f"updates/live_inbox/{typ}/{fpath.name}"})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)[:200]}, 500)

    def _backup_status(self) -> dict:
        """Liste compacte des dernieres sauvegardes par appareil (lecture seule)."""
        out = {"base": "backups/local_data", "devices": {}}
        try:
            for dev in sorted(ALLOWED_DEVICES):
                d = BACKUP_BASE / dev
                if d.is_dir():
                    files = sorted([p.name for p in d.glob("backup_local_data_*.json")])
                    if files:
                        out["devices"][dev] = {"count": len(files), "last": files[-1]}
        except Exception:
            pass
        return out

    def _handle_backup(self) -> None:
        """POST /__gv/backup : ecrit UNIQUEMENT sous backups/local_data/<device>/."""
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        if length <= 0 or length > BACKUP_MAX_BYTES:
            self._send_json({"ok": False, "error": "taille invalide"}, 413)
            return
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "json invalide"}, 400)
            return
        meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
        device = _safe_device(meta.get("device") or payload.get("device") if isinstance(payload, dict) else "unknown")
        # Horodatage cote serveur (jamais le chemin venant du client -> anti-traversee).
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        target_dir = BACKUP_BASE / device
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            fname = f"backup_local_data_{device}_{stamp}.json"
            fpath = target_dir / fname
            # Ecriture atomique (tmp puis remplacement).
            tmp = target_dir / (fname + ".tmp")
            tmp.write_bytes(raw)
            os.replace(tmp, fpath)
            rel = f"backups/local_data/{device}/{fname}"
            self._send_json({"ok": True, "path": rel, "bytes": len(raw), "device": device})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)[:200]}, 500)

    def _maybe_redirect(self) -> bool:
        request_path = urlsplit(self.path).path.rstrip("/")
        if request_path in {"", "/index.html"}:
            self.send_response(302)
            self.send_header("Location", ROOT_REDIRECT)
            self.end_headers()
            return True
        if request_path in {"/cockpit", PREFIX + "/cockpit"} and PREFIX != "/cockpit":
            self.send_response(302)
            self.send_header("Location", f"{ACTIVE_PATH}?version={ACTIVE_VERSION}&startup=automatic")
            self.end_headers()
            return True
        if request_path in CANONICAL_PATHS:
            self.send_response(302)
            self.send_header("Location", f"{ACTIVE_PATH}?version={ACTIVE_VERSION}&startup=canonical")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return True
        return False

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/__gv/"):
            if self._handle_presence(parsed):
                return
        if self._maybe_redirect():
            return
        super().do_GET()

    def do_HEAD(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/__gv/"):
            self._send_json({"ok": True})
            return
        if self._maybe_redirect():
            return
        super().do_HEAD()

    def do_POST(self):
        # Ecritures autorisees : sauvegarde locale + boite d'entree memoire centrale.
        p = urlsplit(self.path).path
        if p == "/__gv/backup":
            self._handle_backup()
            return
        if p == "/__gv/live-entry":
            self._handle_live_entry()
            return
        self.send_error(405, "Lecture seule (sauf /__gv/backup et /__gv/live-entry)")

    do_PUT = lambda self: self.send_error(405, "Lecture seule")
    do_PATCH = lambda self: self.send_error(405, "Lecture seule")
    do_DELETE = lambda self: self.send_error(405, "Lecture seule")

    def log_message(self, format_string, *args):
        msg = format_string % args
        if "/__gv/" in msg:
            return  # ne pas polluer la console avec le heartbeat
        print(f"[Gabriel Virtuel] {self.address_string()} - {msg}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serveur local Gabriel Virtuel")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--lan", action="store_true",
                        help="Ecoute sur 0.0.0.0 (appareils du reseau local)")
    parser.add_argument("--host", default=None,
                        help="Adresse d'ecoute explicite (ex. 0.0.0.0). Prioritaire sur --lan.")
    parser.add_argument("--open", choices=["choix", "cockpit"], default=None)
    parser.add_argument("--diagnostic", action="store_true",
                        help="Affiche les interfaces/IP detectees et quitte (aucun serveur lance).")
    args = parser.parse_args()

    os.chdir(SERVE_ROOT)
    bind_host = args.host or ("0.0.0.0" if args.lan else "127.0.0.1")
    lan_active = (bind_host == "0.0.0.0")

    global BIND_HOST, ACTIVE_PORT
    BIND_HOST = bind_host
    ACTIVE_PORT = args.port

    if args.diagnostic:
        info = netinfo(); info["port"] = args.port
        print("=" * 60)
        print("GABRIEL VIRTUEL - DIAGNOSTIC RESEAU")
        print("=" * 60)
        print(f"Interface (bind) : {bind_host}")
        print(f"Port             : {args.port}")
        print(f"Version serveur  : v{ACTIVE_VERSION}")
        print(f"Passerelle       : {info['gateway'] or '(inconnue)'}")
        print("-" * 60)
        print("Interfaces detectees :")
        if info["interfaces"]:
            for x in info["interfaces"]:
                print(f"  {x['iface']:<12} {x['ip']:<16} [{x['kind']}]")
        else:
            print("  (aucune interface IPv4 detectee via ip/ifconfig)")
        print("-" * 60)
        print(f"IP Wi-Fi         : {info['wifi_ip'] or '(aucune)'}")
        print(f"IP hotspot       : {info['hotspot_ip'] or '(aucune)'}")
        print(f"IP mobile/CGNAT  : {info['mobile_ip'] or '(aucune)'}")
        print(f"IP recommandee   : {info['recommended_lan_ip'] or '(aucune)'}")
        if info["recommended_lan_ip"]:
            print(f"URL pour iPhone  : http://{info['recommended_lan_ip']}:{args.port}/00-01_ChoixInterface.html")
        if info["mobile_ip"] and not info["hotspot_ip"]:
            print("ATTENTION : seule une IP mobile/CGNAT (100.64/10) est visible.")
            print("  -> Active le POINT D'ACCES Wi-Fi (hotspot) du Samsung : une IP 192.168.x.1 apparaitra.")
        print("=" * 60)
        return 0
    ip = lan_ip()

    try:
        assert_port_available(args.port)
    except RuntimeError as error:
        print("=" * 72)
        print("ERREUR DE DEMARRAGE GABRIEL VIRTUEL")
        print(error)
        print(f"Version qui aurait ete lancee : v{ACTIVE_VERSION}")
        print("=" * 72)
        return 1

    open_target = args.open or ("choix" if CHOIX_PATH else "cockpit")
    open_rel = ROOT_REDIRECT if open_target == "choix" else (
        f"{ACTIVE_PATH}?version={ACTIVE_VERSION}&startup=automatic")
    local_url = f"http://localhost:{args.port}{open_rel}"
    lan_url = f"http://{ip}:{args.port}{open_rel}"

    server = http.server.ThreadingHTTPServer((bind_host, args.port), ReadOnlyHandler)
    print("=" * 72)
    print("Gabriel Virtuel - serveur local")
    print(f"Mode             : {'LAN (0.0.0.0)' if lan_active else 'LOCAL (127.0.0.1)'}")
    print(f"Dossier servi    : {SERVE_ROOT}")
    print(f"Version cockpit  : v{ACTIVE_VERSION}  (latest = {ACTIVE_COCKPIT.name})")
    print(f"Pointeur latest  : index_gabriel_virtuel_latest.html ({LATEST_SYNC_STATUS})")
    print(f"Port             : {args.port}")
    print(f"Ecoute           : {bind_host}:{args.port}" + ("   (LAN actif)" if lan_active else "   (local seulement)"))
    print(f"ChoixInterface   : http://localhost:{args.port}{CHOIX_PATH or ACTIVE_PATH}")
    print(f"Cockpit latest   : http://localhost:{args.port}{ACTIVE_PATH}")
    print(f"URL canonique    : http://localhost:{args.port}{PREFIX}/go   (favori / raccourci, ne change jamais)")
    print(f"Sauvegarde       : POST {PREFIX}/__gv/backup -> backups/local_data/<device>/ (seule ecriture permise)")
    print(f"Presence reseau  : active (appareils visibles sur chaque page)")
    print(f"URL ouverte      : {local_url}")
    if lan_active:
        print(f"IP locale (LAN)  : {ip}")
        print(f"URL LAN          : {lan_url}")
        print(f"  -> autres appareils : http://{ip}:{args.port}{CHOIX_PATH or ACTIVE_PATH}")
        print(f"  -> URL canonique    : http://{ip}:{args.port}{PREFIX}/go")
        print("-" * 72)
        print("AVERTISSEMENT LAN : accessible aux appareils du meme reseau.")
        print("A utiliser uniquement sur reseau personnel ou hotspot controle.")
    else:
        print("Serveur lie a 127.0.0.1 uniquement (securise). --lan pour le reseau.")
    # (fin affichage)
    print("=" * 72)
    print("Ctrl+C pour arreter.")

    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(local_url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArret du serveur.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
