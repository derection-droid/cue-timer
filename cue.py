#!/usr/bin/env python3
"""
Cue — stage timer, wifi-only mode
---------------------------------
Use this when the venue has no internet (or you don't trust it).
Run it from inside this folder on the moderator's laptop:

    python3 cue.py

Your control screen opens in the browser. Phones/tablets on the SAME wifi scan the
"This wifi only" QR. If the laptop also has internet, the "Anywhere" QR keeps working too.

Options:  --port 8765           pick a different port
          --remote-control      let other devices control the timer too (default: watch only)
          --public URL          your GitHub Pages address for the "Anywhere" QR
                                (or set publicUrl in cue-config.js)

Standard library only, Python 3.7+.
"""
import json, os, re, socket, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, '.cue_state.json')
args = sys.argv[1:]
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default
PORT = int(opt('--port', 8765))
REMOTE_CONTROL = '--remote-control' in args
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
         '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon'}

lock = threading.Lock()
store = {'seq': 0, 'state': None, 'endAt': None}
seen = {}


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))      # sends nothing; just picks the active network interface
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'
    finally:
        s.close()


def github_pages_url():
    """Guess https://OWNER.github.io/REPO/ from this folder's git remote."""
    try:
        with open(os.path.join(HERE, '.git', 'config')) as f:
            m = re.search(r'url\s*=\s*\S*github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?\s*$', f.read(), re.M)
        if m:
            owner, repo = m.group(1), m.group(2)
            if repo.lower() == owner.lower() + '.github.io':
                return 'https://%s.github.io/' % owner.lower()
            return 'https://%s.github.io/%s/' % (owner.lower(), repo)
    except Exception:
        pass
    return ''


IP = lan_ip()
LOCAL_IPS = {'127.0.0.1', '::1', IP}
PUBLIC = opt('--public', '') or github_pages_url()
if PUBLIC and not PUBLIC.endswith('/'):
    PUBLIC += '/'


def load():
    try:
        with open(STATE_FILE) as f:
            st = json.load(f).get('state')
        if st and isinstance(st.get('segs'), list):
            st['run'] = False                    # never resume running after a restart
            store['state'], store['seq'] = st, 1
    except Exception:
        pass


def current():
    st = store['state']
    if not st:
        return None
    st = dict(st)
    if st.get('run') and store['endAt'] is not None:
        st['rem'] = round((store['endAt'] - time.monotonic()) * 1000)
    return st


def persist():
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({'state': current()}, f)
    except Exception:
        pass


def config_js(local):
    try:
        with open(os.path.join(HERE, 'cue-config.js'), encoding='utf-8') as f:
            base = f.read()
    except Exception:
        base = 'window.CUE = window.CUE || {};'
    extra = {'server': True, 'local': bool(local), 'url': 'http://%s:%d/out' % (IP, PORT)}
    return (base + '\n;(function(c,x,p){Object.assign(c,x);if(!c.publicUrl)c.publicUrl=p;})(window.CUE,'
            + json.dumps(extra) + ',' + json.dumps(PUBLIC) + ');\n').encode('utf-8')


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def ip(self):
        return self.client_address[0].replace('::ffff:', '')

    def can_control(self):
        return REMOTE_CONTROL or self.ip() in LOCAL_IPS

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def file(self, rel):
        p = os.path.normpath(os.path.join(HERE, rel))
        if not p.startswith(HERE + os.sep) or not os.path.isfile(p):
            return self.send(404, b'not found', 'text/plain')
        with open(p, 'rb') as f:
            self.send(200, f.read(), TYPES.get(os.path.splitext(p)[1], 'application/octet-stream'))

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html'):
            if not self.can_control():          # phones that open the root get the panel view
                self.send_response(302); self.send_header('Location', '/out'); self.end_headers(); return
            return self.file('index.html')
        if path == '/out':
            return self.file('index.html')
        if path == '/cue-config.js':
            return self.send(200, config_js(self.can_control()), TYPES['.js'])
        if path == '/state':
            t = time.monotonic()
            with lock:
                seen[self.ip()] = t
                for k in [k for k, v in seen.items() if t - v > 4]:
                    del seen[k]
                body = {'seq': store['seq'], 'state': current(), 'clients': len(seen)}
            return self.send(200, json.dumps(body).encode(), 'application/json')
        if path.startswith('/vendor/'):
            return self.file(path.lstrip('/'))
        self.send(404, b'not found', 'text/plain')

    def do_POST(self):
        if urlparse(self.path).path != '/state':
            return self.send(404, b'not found', 'text/plain')
        if not self.can_control():
            return self.send(403, b'{"error":"view only"}', 'application/json')
        try:
            n = int(self.headers.get('Content-Length', 0))
            d = json.loads(self.rfile.read(min(n, 200000)) or b'{}')
            assert isinstance(d.get('segs'), list) and d['segs']
        except Exception:
            return self.send(400, b'{"error":"bad state"}', 'application/json')
        with lock:
            store['state'] = d
            store['endAt'] = time.monotonic() + float(d.get('rem') or 0) / 1000.0 if d.get('run') else None
            store['seq'] += 1
            seq = store['seq']
        threading.Thread(target=persist, daemon=True).start()
        self.send(200, json.dumps({'seq': seq}).encode(), 'application/json')


def main():
    global PORT
    load()
    srv = None
    for p in range(PORT, PORT + 20):
        try:
            srv = ThreadingHTTPServer(('0.0.0.0', p), H)
            PORT = p
            break
        except OSError:
            continue
    if not srv:
        print('Could not open a port. Try: python3 cue.py --port 9000'); sys.exit(1)
    srv.daemon_threads = True
    ctrl = 'http://127.0.0.1:%d/' % PORT
    print('\n  CUE — stage timer is running\n')
    print('  Control (this laptop):     ' + ctrl)
    print('  Panel view (same wifi):    http://%s:%d/out' % (IP, PORT))
    print('  "Anywhere" QR points to:   ' + (PUBLIC or '(not set — add publicUrl in cue-config.js)'))
    if IP.startswith('127.'):
        print('\n  ! No network found — connect this laptop to the wifi or a hotspot, then restart.')
    print('\n  Keep this window open. Press Ctrl+C to stop.\n')
    try:
        webbrowser.open(ctrl)
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n  Stopped.')


if __name__ == '__main__':
    main()
