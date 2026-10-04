"""Local HTTP app. No model calls, trackers, or external script dependencies."""
import argparse
import json
import secrets
import sqlite3
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import lab
import knowledge_graph as kg
from import_data import seed

TOKEN=secrets.token_hex(24)

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address=False
    def server_bind(self):
        if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

class Handler(BaseHTTPRequestHandler):
    def reply(self,data,status=200,mime='application/json',filename=None):
        body=data if isinstance(data,bytes) else (json.dumps(data,ensure_ascii=False,allow_nan=False) if mime=='application/json' else data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime+'; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers(); self.wfile.write(body)

    def authorized_host(self):
        return self.headers.get('Host') in [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']

    def do_GET(self):
        if not self.authorized_host(): return self.reply({'error':'Local host required.'},403)
        parsed=urlparse(self.path); p=parsed.path; q=parse_qs(parsed.query)
        arg=lambda k,d='':q.get(k,[d])[0]
        try:
            if p in ['/fonts/et-book-roman-line-figures.woff2','/fonts/et-book-italic.woff2','/fonts/et-book-bold-line-figures.woff2']:
                return self.reply((lab.ROOT/'static'/p[1:]).read_bytes(),mime='font/woff2')
            if p in ['/gsap.min.js','/demo-player.js','/graph.js','/graph-space.js','/vendor/three.module.js','/vendor/three.core.js','/vendor/OrbitControls.js']:
                return self.reply((lab.ROOT/'static'/p[1:]).read_text(encoding='utf-8'),mime='text/javascript')
            if p in ['/','/app.js','/hosted-storage.js','/home.js','/demo.html','/demo.js','/demo.css','/style.css']:
                name={'/':'index.html','/app.js':'app.js','/hosted-storage.js':'hosted-storage.js','/home.js':'home.js','/demo.html':'demo.html','/demo.js':'demo.js','/demo.css':'demo.css','/style.css':'style.css'}[p]
                mime={'/':'text/html','/app.js':'text/javascript','/hosted-storage.js':'text/javascript','/home.js':'text/javascript','/demo.html':'text/html','/demo.js':'text/javascript','/demo.css':'text/css','/style.css':'text/css'}[p]
                return self.reply((lab.ROOT/'static'/name).read_text(encoding='utf-8'),mime=mime)
            if p=='/api/session': return self.reply({'token':TOKEN})
            if p=='/api/research': return self.reply(json.loads((lab.ROOT/'research.json').read_text(encoding='utf-8')))
            if p=='/api/examples': return self.reply({k:json.loads((lab.ROOT/f'fixtures/{k}-demo.json').read_text()) for k in ['cooperation','audit','hybrid']})
            with lab.connect(self.server.db) as con:
                if p=='/api/graph': data=kg.board_case() if arg('case')=='board' else kg.village_case(con) if arg('case')=='village' else kg.record_graph(con,arg('q'),arg('source'))
                elif p=='/api/summary': data=lab.summary(con)
                elif p=='/api/search': data=lab.find_events(con,arg('q')[:500],arg('source'),max(0,int(arg('offset','0'))),channel=arg('channel'))
                elif p=='/api/trace':
                    if not arg('q').strip(): raise ValueError('Enter a URL or a distinctive phrase.')
                    data=lab.trace(con,arg('q')[:500],arg('source'))
                elif p=='/api/event':
                    row=con.execute('SELECT * FROM events WHERE key=?',(arg('key'),)).fetchone()
                    if not row: return self.reply({'error':'Record not found.'},404)
                    data=lab.unpack(row,True)
                    data['references']=[dict(x) for x in con.execute('SELECT * FROM links WHERE event_key=?',(arg('key'),))]
                    parent=data['meta'].get('parent_id')
                    if parent: data['parent_key']='swarmtraces:'+parent
                elif p=='/api/candidates': data=lab.candidates(con)
                elif p=='/api/activity': data=lab.activity(con,arg('source','ai-village'),arg('window','daily'))
                elif p=='/api/reviews': data=lab.reviews(con)
                elif p=='/api/report': return self.reply(lab.report(con,arg('id')),mime='text/markdown',filename='evidence-review.md')
                elif p=='/api/experiments': data=[dict(x) for x in con.execute('SELECT id,kind FROM experiments')]
                elif p in ['/api/cooperation','/api/audit','/api/hybrid']:
                    kind=p.rsplit('/',1)[1]
                    row=con.execute('SELECT body FROM experiments WHERE id=? AND kind=?',(arg('id',kind+'-demo'),kind)).fetchone()
                    if not row: return self.reply({'error':'Experiment not found.'},404)
                    body=json.loads(row[0])
                    if kind=='cooperation': data=lab.cooperation(body['records'])
                    elif kind=='hybrid': data=lab.hybrid(body['records'],float(arg('budget','5')))
                    else: data=lab.selectivity(body['records'],float(arg('budget','5')),float(arg('selectivity','10')))
                    data['dataset']={k:v for k,v in body.items() if k!='records'}
                else: return self.reply({'error':'Not found.'},404)
            return self.reply(data)
        except (ValueError,TypeError,sqlite3.OperationalError) as e: return self.reply({'error':str(e)},400)

    def do_POST(self):
        origin=self.headers.get('Origin')
        valid=[f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']
        if not self.authorized_host() or self.headers.get('X-Lab-Token')!=TOKEN or (origin and origin not in valid):
            return self.reply({'error':'Open this app locally to save changes.'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 10*1024*1024: raise ValueError('Provide a JSON file smaller than 10 MB.')
            body=json.loads(self.rfile.read(length))
            with lab.connect(self.server.db) as con:
                if self.path=='/api/reviews': result=lab.save_review(con,body)
                elif self.path=='/api/experiments':
                    if not isinstance(body,dict): raise ValueError('Experiment must be an object.')
                    kind=body.get('kind'); name=body.get('name')
                    if kind not in ['cooperation','audit','hybrid'] or not isinstance(name,str) or not name.strip(): raise ValueError('Experiment kind and name are required.')
                    records=body.get('records')
                    if kind=='cooperation': lab.validate_runs(records)
                    elif kind=='hybrid': lab.hybrid(records)
                    else: lab.validate_episodes(records)
                    if not isinstance(body.get('synthetic'),bool): raise ValueError('Declare whether the records are synthetic.')
                    clean={'name':name[:100],'synthetic':body['synthetic'],'description':str(body.get('description',''))[:1000], 'records':records}
                    eid=secrets.token_hex(8)
                    con.execute('INSERT INTO experiments VALUES (?,?,?)',(eid,kind,json.dumps(clean,allow_nan=False))); con.commit()
                    result={'id':eid,'kind':kind}
                else: return self.reply({'error':'Not found.'},404)
            return self.reply(result,201)
        except (ValueError,TypeError,KeyError) as e: return self.reply({'error':str(e)},400)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8877)
    parser.add_argument('--db',default=str(lab.DB))
    args=parser.parse_args()
    with lab.connect(args.db) as con:
        lab.initialize(con)
        # Do not overwrite demo fixtures on every start after import.
        if not con.execute('SELECT 1 FROM imports WHERE source="demo"').fetchone(): seed(con)
    server=LocalServer(('127.0.0.1',args.port),Handler); server.db=args.db
    print(f'Swarm Evidence Lab: http://127.0.0.1:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
