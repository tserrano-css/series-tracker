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

PORT = 8080

# name exposed to the web UI -> actual script file
ALLOWED_SCRIPTS = {
    'filmaffinity': 'fetch_filmaffinity.py',
}

job_state = {'running': False, 'output': '', 'done': False, 'error': None}


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

    def do_GET(self):
        if self.path == '/script-status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(job_state).encode())
        else:
            super().do_GET()


if __name__ == '__main__':
    print(f"Servint series-tracker a http://localhost:{PORT}")
    print("Endpoint local: POST /run-script  { name: 'filmaffinity' }")
    http.server.ThreadingHTTPServer(('localhost', PORT), Handler).serve_forever()
