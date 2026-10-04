"""Hosted demo: synthetic records, temporary calculations, no shared user storage."""
import json
import secrets
from urllib.parse import parse_qs, urlparse

import lab
import knowledge_graph as kg
from app import Handler
from import_data import seed


def demo_connection():
    con = lab.connect(':memory:')
    lab.initialize(con)
    seed(con)
    return con


def calculate(kind, records, budget=5, selectivity=10):
    if kind == 'cooperation':
        return lab.cooperation(records)
    if kind == 'hybrid':
        return lab.hybrid(records, float(budget))
    if kind == 'audit':
        return lab.selectivity(records, float(budget), float(selectivity))
    raise ValueError('Unknown experiment kind.')


class handler(Handler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        args = parse_qs(parsed.query)
        arg = lambda key, default='': args.get(key, [default])[0]
        try:
            if path in ['/fonts/et-book-roman-line-figures.woff2','/fonts/et-book-italic.woff2','/fonts/et-book-bold-line-figures.woff2']:
                return self.reply((lab.ROOT/'static'/path[1:]).read_bytes(), mime='font/woff2')
            if path in ['/gsap.min.js', '/demo-player.js', '/graph.js', '/graph-space.js', '/vendor/three.module.js', '/vendor/three.core.js', '/vendor/OrbitControls.js']:
                return self.reply((lab.ROOT/'static'/path[1:]).read_text(encoding='utf-8'), mime='text/javascript')
            if path in ['/', '/app.js', '/hosted-storage.js', '/home.js', '/demo.html', '/demo.js', '/demo.css', '/style.css']:
                name = {'/': 'index.html', '/app.js': 'app.js', '/hosted-storage.js': 'hosted-storage.js', '/home.js': 'home.js', '/demo.html': 'demo.html', '/demo.js': 'demo.js', '/demo.css': 'demo.css', '/style.css': 'style.css'}[path]
                mime = {'/': 'text/html', '/app.js': 'text/javascript', '/hosted-storage.js': 'text/javascript', '/home.js': 'text/javascript', '/demo.html': 'text/html', '/demo.js': 'text/javascript', '/demo.css': 'text/css', '/style.css': 'text/css'}[path]
                return self.reply((lab.ROOT/'static'/name).read_text(encoding='utf-8'), mime=mime)
            if path == '/api/session':
                return self.reply({'token': '', 'hosted': True})
            if path == '/api/research':
                return self.reply(json.loads((lab.ROOT/'research.json').read_text(encoding='utf-8')))
            if path == '/api/examples':
                return self.reply({kind: json.loads((lab.ROOT/f'fixtures/{kind}-demo.json').read_text())
                                   for kind in ['cooperation', 'audit', 'hybrid']})
            with demo_connection() as con:
                if path == '/api/graph':
                    data = kg.completion_case() if arg('case') == 'example' else kg.record_graph(con, arg('q')[:500], arg('source'))
                elif path == '/api/summary':
                    data = lab.summary(con)
                elif path == '/api/search':
                    data = lab.find_events(con, arg('q')[:500], arg('source'),
                                           max(0, int(arg('offset', '0'))), channel=arg('channel'))
                elif path == '/api/trace':
                    if not arg('q').strip():
                        raise ValueError('Enter a URL or a distinctive phrase.')
                    data = lab.trace(con, arg('q')[:500], arg('source'))
                elif path == '/api/event':
                    row = con.execute('SELECT * FROM events WHERE key=?', (arg('key'),)).fetchone()
                    if not row:
                        return self.reply({'error': 'Record not found.'}, 404)
                    data = lab.unpack(row, True)
                    data['references'] = [dict(x) for x in con.execute(
                        'SELECT * FROM links WHERE event_key=?', (arg('key'),))]
                elif path == '/api/candidates':
                    data = lab.candidates(con)
                elif path == '/api/activity':
                    data = lab.activity(con, arg('source', 'demo'), arg('window', 'daily'))
                elif path == '/api/experiments':
                    data = [dict(x) for x in con.execute('SELECT id,kind FROM experiments')]
                elif path in ['/api/cooperation', '/api/audit', '/api/hybrid']:
                    kind = path.rsplit('/', 1)[1]
                    row = con.execute('SELECT body FROM experiments WHERE id=? AND kind=?',
                                      (arg('id', kind+'-demo'), kind)).fetchone()
                    if not row:
                        return self.reply({'error': 'Experiment not found.'}, 404)
                    body = json.loads(row[0])
                    data = calculate(kind, body['records'], arg('budget', '5'), arg('selectivity', '10'))
                    data['dataset'] = {key: value for key, value in body.items() if key != 'records'}
                else:
                    return self.reply({'error': 'Not found.'}, 404)
            return self.reply(data)
        except (ValueError, TypeError, KeyError) as error:
            return self.reply({'error': str(error)}, 400)

    def do_POST(self):
        # No persistent writes. Reject browser requests from other origins.
        origin = self.headers.get('Origin')
        host = self.headers.get('Host')
        if origin and origin not in [f'https://{host}', f'http://{host}']:
            return self.reply({'error': 'Open this app to submit results.'}, 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 10*1024*1024:
                raise ValueError('Provide a JSON file smaller than 10 MB.')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('Provide a JSON object.')
            path = urlparse(self.path).path
            if path == '/api/calculate':
                result = calculate(body.get('kind'), body.get('records'),
                                   body.get('budget', 5), body.get('selectivity', 10))
            elif path == '/api/experiment/check':
                name = body.get('name')
                if not isinstance(name, str) or not name.strip() or not isinstance(body.get('synthetic'), bool):
                    raise ValueError('Experiment name and synthetic declaration are required.')
                kind = body.get('kind')
                calculate(kind, body.get('records'))
                result = {'id': secrets.token_hex(8), 'kind': kind}
            elif path in ['/api/review/check', '/api/report/render']:
                with demo_connection() as con:
                    result = lab.save_review(con, body)
                    if path == '/api/report/render':
                        result = {'text': lab.report(con, result['id'])}
            else:
                return self.reply({'error': 'Not found.'}, 404)
            return self.reply(result)
        except (ValueError, TypeError, KeyError) as error:
            return self.reply({'error': str(error)}, 400)
