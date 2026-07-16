#!/usr/bin/env python3
"""Serveur HTTP local en lecture seule pour Gabriel AXA.

Sert la racine du dépôt en statique — exactement le comportement de la version déployée
(GitHub Pages). `index.html` gère déjà la redirection vers `app/` (balise meta-refresh) ;
ce serveur n'a donc aucune logique applicative à porter, juste des en-têtes sûrs par défaut
et un cache désactivé pour un développement local sans surprise.

Usage :
  python start_local_server.py                  -> http://127.0.0.1:8787/
  python start_local_server.py --port 8790
  python start_local_server.py --lan             -> accessible aux appareils du réseau local
  python start_local_server.py --no-browser      -> ne pas ouvrir le navigateur automatiquement
"""

from __future__ import annotations

import argparse
import http.server
import threading
import webbrowser
from pathlib import Path

DEFAULT_PORT = 8787
SERVE_ROOT = Path(__file__).resolve().parent


class ReadOnlyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SERVE_ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    # Lecture seule : aucune écriture disque possible depuis ce serveur.
    def do_POST(self):
        self.send_error(405, "Lecture seule")

    do_PUT = lambda self: self.send_error(405, "Lecture seule")
    do_PATCH = lambda self: self.send_error(405, "Lecture seule")
    do_DELETE = lambda self: self.send_error(405, "Lecture seule")

    def log_message(self, format_string, *args):
        print(f"[Gabriel AXA] {self.address_string()} - {format_string % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serveur local Gabriel AXA")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--lan", action="store_true", help="Écoute sur 0.0.0.0 (réseau local)")
    args = parser.parse_args()

    bind_host = "0.0.0.0" if args.lan else "127.0.0.1"
    server = http.server.ThreadingHTTPServer((bind_host, args.port), ReadOnlyHandler)
    local_url = f"http://localhost:{args.port}/"

    print("=" * 60)
    print("Gabriel AXA — serveur local (lecture seule)")
    print(f"Dossier servi : {SERVE_ROOT}")
    print(f"Écoute        : {bind_host}:{args.port}" + ("  (réseau local actif)" if args.lan else "  (local seulement)"))
    print(f"URL           : {local_url}  (redirige vers app/)")
    print("=" * 60)
    print("Ctrl+C pour arrêter.")

    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(local_url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
