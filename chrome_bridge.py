"""Authenticated loopback bridge for the ASUNA Chrome extension."""
import concurrent.futures
import copy
import hmac
import json
import queue
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 17653
ALLOWED = {'open', 'read', 'open_item', 'click', 'fill', 'search', 'approve', 'back',
           'forward', 'reload', 'scroll', 'find', 'tabs', 'switch_tab', 'media'}
CONNECT_HTML = '''<!doctype html><meta charset="utf-8"><title>Connect ASUNA</title>
<style>body{background:#080e17;color:#edf5ff;font:18px system-ui;max-width:650px;margin:10vh auto;padding:24px}
button{background:#68e7ec;border:0;padding:14px 24px;font:inherit;cursor:pointer}p{line-height:1.6}</style>
<h1>Connect ASUNA to this Chrome profile</h1>
<p>Load the ASUNA Browser Companion extension in this profile first. Then press Connect.
ASUNA can read and act on ordinary webpages when you ask. Browser traffic stays on this computer.</p>
<button id="connect">Connect ASUNA</button><p id="status">Waiting for you.</p>'''


class ProfileBridge:
    def __init__(self, data, port=PORT):
        self.data = Path(data)
        self.port = port
        self.lock = threading.Lock()
        self.command_lock = threading.Lock()
        self.jobs = queue.Queue()
        self.pending = {}
        self.server = self.thread = None
        self.last_seen = 0
        self.origin = None
        self.cache = {'url': '', 'title': '', 'items': [], 'token': ''}
        self.token = None
        self.pair_code = None
        self.pair_deadline = 0
        self.closed = False

    def start(self):
        with self.lock:
            if self.closed:
                raise RuntimeError('The Chrome bridge is closed.')
            if self.server:
                return
            self.data.mkdir(parents=True, exist_ok=True)
            path = self.data / 'chrome-bridge.json'
            try:
                token = json.loads(path.read_text(encoding='utf-8'))['token']
                if not re.fullmatch(r'[0-9a-f]{64}', token):
                    raise ValueError('Invalid pairing token')
            except (OSError, ValueError, KeyError, TypeError):
                token = secrets.token_hex(32)
                path.write_text(json.dumps({'token': token}), encoding='utf-8')
            bridge = self

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass  # No URLs, pairing secrets, or page content in HTTP logs.

                def reply(self, code, value, content_type='application/json'):
                    body = value.encode() if isinstance(value, str) else json.dumps(value).encode()
                    self.send_response(code)
                    origin = self.headers.get('Origin', '')
                    if re.fullmatch(r'chrome-extension://[a-p]{32}', origin):
                        self.send_header('Access-Control-Allow-Origin', origin)
                        self.send_header('Vary', 'Origin')
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'")
                    self.end_headers()
                    self.wfile.write(body)

                def valid_host(self):
                    return self.headers.get('Host') == f'127.0.0.1:{bridge.port}'

                def do_OPTIONS(self):
                    if not self.valid_host() or not re.fullmatch(r'chrome-extension://[a-p]{32}', self.headers.get('Origin', '')):
                        return self.reply(403, {'error': 'Extension access only.'})
                    self.send_response(204)
                    self.send_header('Access-Control-Allow-Origin', self.headers['Origin'])
                    self.send_header('Access-Control-Allow-Methods', 'POST')
                    self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
                    self.end_headers()

                def do_GET(self):
                    if not self.valid_host():
                        return self.reply(403, {'error': 'Invalid host.'})
                    if self.path == '/connect':
                        return self.reply(200, CONNECT_HTML, 'text/html; charset=utf-8')
                    return self.reply(404, {'error': 'Not found.'})

                def do_POST(self):
                    origin = self.headers.get('Origin', '')
                    try:
                        length = int(self.headers.get('Content-Length', '0'))
                        if not 0 < length <= 262144:
                            raise ValueError('Invalid request size')
                        body = json.loads(self.rfile.read(length))
                        if not isinstance(body, dict):
                            raise ValueError('Invalid request')
                    except (ValueError, OSError):
                        return self.reply(400, {'error': 'Invalid request.'})
                    authorization = self.headers.get('Authorization', '')
                    is_pair = self.path == '/pair'
                    secret = bridge.pair_code if is_pair else bridge.token
                    if (not self.valid_host() or not re.fullmatch(r'chrome-extension://[a-p]{32}', origin) or
                            not secret or not hmac.compare_digest(authorization, 'Bearer ' + secret) or
                            (is_pair and time.monotonic() > bridge.pair_deadline)):
                        return self.reply(403, {'error': 'Pair the ASUNA extension in your selected profile.'})
                    if self.path == '/status':
                        return self.reply(200, {'connected': bridge.connected() and bridge.origin == origin})
                    with bridge.lock:
                        current_secret = bridge.pair_code if is_pair else bridge.token
                        if (bridge.closed or not current_secret or
                                not hmac.compare_digest(authorization, 'Bearer ' + current_secret) or
                                (is_pair and time.monotonic() > bridge.pair_deadline)):
                            return self.reply(403, {'error': 'Open a fresh connection page from ASUNA.'})
                        if is_pair:
                            # Browser history only sees a short-lived, single-use code.
                            bridge.pair_code = None
                            bridge.token = secrets.token_hex(32)
                            (bridge.data / 'chrome-bridge.json').write_text(json.dumps({'token': bridge.token}), encoding='utf-8')
                            bridge.origin = origin
                        if bridge.origin and bridge.origin != origin:
                            return self.reply(403, {'error': 'Another extension is already paired.'})
                        bridge.origin = origin
                        bridge.last_seen = time.monotonic()
                    if self.path == '/pair':
                        return self.reply(200, {'ok': True, 'token': bridge.token})
                    if self.path == '/disconnect':
                        with bridge.lock:
                            bridge.origin = None
                            bridge.last_seen = 0
                            bridge.cache = {'url': '', 'title': '', 'items': [], 'token': ''}
                            for future in bridge.pending.values():
                                if not future.done():
                                    future.set_exception(RuntimeError('The Chrome extension was disconnected.'))
                            bridge.pending.clear()
                            while True:
                                try:
                                    bridge.jobs.get_nowait()
                                except queue.Empty:
                                    break
                        bridge.jobs.put(None)
                        return self.reply(200, {'ok': True})
                    if self.path == '/poll':
                        try:
                            job = bridge.jobs.get(timeout=15)
                            while job and time.monotonic() > job['expires']:
                                job = bridge.jobs.get(timeout=1)
                        except queue.Empty:
                            job = None
                        # A previous profile's in-flight poll cannot take a new job after pairing changes.
                        if not hmac.compare_digest(authorization, 'Bearer ' + bridge.token) or not bridge.connected():
                            if job:
                                bridge.jobs.put(job)
                            return self.reply(403, {'error': 'Reconnect this profile.'})
                        return self.reply(200, {'job': job})
                    if self.path == '/result':
                        with bridge.lock:
                            future = bridge.pending.pop(body.get('id'), None)
                        if future and not future.done():
                            if isinstance(body.get('error'), str):
                                future.set_exception(RuntimeError(body['error'][:1000]))
                            elif isinstance(body.get('result'), dict):
                                future.set_result(body['result'])
                            else:
                                future.set_exception(RuntimeError('Invalid extension response.'))
                        return self.reply(200, {'ok': bool(future)})
                    return self.reply(404, {'error': 'Not found.'})

            self.token = token
            try:
                self.server = ThreadingHTTPServer(('127.0.0.1', self.port), Handler)
            except OSError as exc:
                raise RuntimeError('The ASUNA Chrome connection is already in use. Close older ASUNA windows, then reopen ASUNA.') from exc
            self.port = self.server.server_port
            self.thread = threading.Thread(target=self.server.serve_forever, name='ASUNA-Extension', daemon=True)
            self.thread.start()

    def connected(self):
        return bool(self.origin and time.monotonic() - self.last_seen < 25)

    def cached(self):
        with self.lock:
            if not self.connected():
                return {'url': '', 'title': '', 'items': [], 'token': ''}
            value = copy.deepcopy(self.cache)
        value.pop('text', None)
        value['items'] = [{key: item.get(key, '') for key in ('id', 'role', 'name', 'href', 'type', 'video', 'result')}
                          for item in value.get('items', [])[:40]]
        for item in value['items']:
            item['name'] = item['name'][:100]
            item['href'] = item['href'][:180]
        return value

    def call(self, action, text='', number=0):
        if action not in ALLOWED or not isinstance(text, str) or len(text) > 16000 or type(number) is not int:
            raise ValueError('Unsupported browser command.')
        self.start()
        if not self.connected():
            raise RuntimeError('The page-control connection is not ready. Type connect browser in ASUNA, then click the Connect ASUNA button INSIDE the Chrome page that opens. Opening the tab alone does not connect it. Load ASUNA Browser Companion first if needed.')
        with self.command_lock:
            ticket = secrets.token_hex(16)
            future = concurrent.futures.Future()
            with self.lock:
                self.pending[ticket] = future
            self.jobs.put({'id': ticket, 'action': action, 'text': text, 'number': number,
                           'expires': time.monotonic() + 40})
            try:
                result = future.result(timeout=42)
            except concurrent.futures.TimeoutError:
                future.cancel()
                raise TimeoutError('Chrome did not finish the action. Check the page before retrying; ASUNA did not retry it.') from None
            finally:
                with self.lock:
                    self.pending.pop(ticket, None)
            snapshot = result.pop('snapshot', None)
            if isinstance(snapshot, dict):
                with self.lock:
                    self.cache = snapshot
            return result

    def connect(self, profile):
        from browser_profile import launch
        self.start()
        if self.connected():
            return 'Your selected Chrome profile is already connected. Page controls are ready.'
        with self.lock:
            self.pair_code = secrets.token_hex(32)
            self.pair_deadline = time.monotonic() + 180
            code = self.pair_code
        launch(f'http://127.0.0.1:{self.port}/connect#' + code, profile)
        return 'Opened the connection page in your selected Chrome profile. Click the Connect ASUNA button INSIDE that page and wait for Connected. Opening the tab alone does not connect it. Load the extension first if needed.'

    def close(self):
        self.closed = True
        with self.lock:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(RuntimeError('ASUNA closed the Chrome connection.'))
            self.pending.clear()
        self.jobs.put(None)
        if self.server:
            self.server.shutdown()
            self.server.server_close()
