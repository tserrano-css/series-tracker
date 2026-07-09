#!/usr/bin/env python3
"""
Local dev server for series-tracker.
Serves the static files (like http.server) AND exposes an endpoint to
launch local Python scripts (e.g. fetch_filmaffinity.py) from the web UI.

Only meant to run on your own PC — never deploy this to a public host.

Usage: python local_server.py
"""
import http.server
import json
import subprocess
import sys
import threading
from urllib.parse import urlparse, parse_qs

PORT = 8080

# name exposed to the web UI -> actual script file
ALLOWED_SCRIPTS = {
    'filmaffinity': 'fetch_filmaffinity.py',
}

job_state = {'running': False, 'output': '', 'done': False, 'error': None}

# ── Persistent browser for single-series score lookups (IMDB + Filmaffinity) ──
# Lazily created on first /fetch-scores call. Reused across calls so the
# Cloudflare/IMDB challenge is only solved once. Guarded by a lock because
# ThreadingHTTPServer may handle requests concurrently.
_driver = None
_driver_lock = threading.Lock()


def get_driver():
    """Return a live browser session, recreating it if the previous one died.

    undetected-chromedriver drives a *visible* Chrome window; if it gets closed
    (manually, or by a crash) the session becomes invalid and every scrape
    returns None forever. So we probe the session on each use and respawn it
    when it's dead, instead of only creating one when `_driver is None`."""
    global _driver
    if _driver is not None:
        try:
            _ = _driver.current_url        # cheap liveness probe
        except Exception:
            print('  Sessió de navegador morta → recreant-la…')
            try:
                _driver.quit()
            except Exception:
                pass
            _driver = None
    if _driver is None:
        import fetch_filmaffinity as F
        _driver = F.make_driver()
    return _driver


def fetch_scores(imdb_url, title, year, fa_url):
    """Return {imdb, fa, fa_url} scraped with the real browser."""
    import fetch_filmaffinity as F
    out = {'imdb': None, 'fa': None, 'fa_url': fa_url or None}
    with _driver_lock:
        driver = get_driver()
        if imdb_url:
            out['imdb'] = F.imdb_score(driver, imdb_url)
        if fa_url:
            out['fa'] = F.score_from_url(driver, fa_url)
        elif title:
            score, found_url = F.search_score(driver, title, year)
            out['fa'] = score
            out['fa_url'] = found_url
    return out


def run_script(script_file):
    job_state.update({'running': True, 'output': '', 'done': False, 'error': None})
    try:
        proc = subprocess.Popen(
            [sys.executable, script_file],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', bufsize=1
        )
        for line in proc.stdout:
            job_state['output'] += line
        proc.wait()
        if proc.returncode != 0:
            job_state['error'] = f'Script terminado con código {proc.returncode}'
    except Exception as e:
        job_state['error'] = str(e)
    finally:
        job_state['running'] = False
        job_state['done'] = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path == '/run-script':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length) or b'{}')
            name = body.get('name')
            script_file = ALLOWED_SCRIPTS.get(name)

            if not script_file:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Script no permès'}).encode())
                return

            if job_state['running']:
                self.send_response(409)
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Ja hi ha un script executant-se'}).encode())
                return

            threading.Thread(target=run_script, args=(script_file,), daemon=True).start()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'started': True}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, obj, status=200):
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(obj).encode())
        except (ConnectionResetError, BrokenPipeError):
            # El navegador ha tancat la connexió (p.ex. clics solapats mentre
            # una crida lenta encara corria). No cal fer soroll.
            print('  (client desconnectat abans de rebre la resposta)')

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/script-status':
            self._send_json(job_state)
        elif parsed.path == '/fetch-scores':
            q = parse_qs(parsed.query)
            imdb_url = q.get('imdb_url', [''])[0]
            title    = q.get('title', [''])[0]
            year     = q.get('year', [''])[0]
            fa_url   = q.get('fa_url', [''])[0]
            try:
                result = fetch_scores(imdb_url, title,
                                      int(year) if year.isdigit() else None,
                                      fa_url)
                self._send_json(result)
            except Exception as e:
                self._send_json({'error': str(e)}, status=500)
        else:
            super().do_GET()


def _cleanup():
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None


if __name__ == '__main__':
    import atexit
    atexit.register(_cleanup)
    print(f"Servint series-tracker a http://localhost:{PORT}")
    print("Endpoints: POST /run-script · GET /fetch-scores?imdb_url&title&year&fa_url")
    try:
        http.server.ThreadingHTTPServer(('localhost', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup()
