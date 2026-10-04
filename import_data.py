"""Read existing datasets into a local index. Recorded programs are never executed."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from lab import DB, add_event, connect, initialize

def rows(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',encoding='utf-8') as f:
        for n,line in enumerate(f,1):
            if line.strip(): yield n,json.loads(line)

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def utc(value):
    if not value: return None
    return value.replace(' ','T') + ('' if value.endswith('Z') or '+' in value else 'Z')

def begin(con,source):
    for table,column in [('search','key'),('links','event_key')]:
        con.execute(f'DELETE FROM {table} WHERE {column} IN (SELECT key FROM events WHERE source=?)',(source,))
    con.execute('DELETE FROM events WHERE source=?',(source,))

def finish(con,source,count,path,scope,limits):
    con.execute('INSERT OR REPLACE INTO imports VALUES (?,?,?)',(source,count,json.dumps({
        'scope':scope,'limits':limits,'filename':path.name,'sha256':digest(path)})))
    con.commit()
    print(f'{source}: {count:,} records',flush=True)

def village(con,folder,research):
    agents={x['id']:x for _,x in rows(folder/'agents.jsonl.gz')}
    path=folder/'chat_messages.jsonl.gz'
    begin(con,'ai-village'); count=0
    for line,x in rows(path):
        a=agents.get(x.get('agent_speaker_id'),{})
        meta={'line':line,'filename':path.name,'speaker_type':x['speaker_type'],
              'model_current_metadata':a.get('model_string'), 'historical_model':'unknown',
              'identity':'Dataset agent record' if a else 'Human contributor or unknown',
              'operator_independence':'not established', 'permission':'not established from message alone'}
        add_event(con,'ai-village',x['id'],x.get('content') or '',time=utc(x.get('created_at')),
                  actor=a.get('name') or 'Human contributor',channel=x.get('room_id'),meta=meta,
                  url='https://huggingface.co/datasets/aidigestorg/ai-village')
        count+=1
    # The bounded sample is clearly identified. Full turns remain on drive D.
    sample=research/'data/ai-village/computer_use_turns.first-250.jsonl'
    if sample.exists():
        wanted={x['session_id'] for _,x in rows(sample)}
        sessions={x['id']:x for _,x in rows(folder/'computer_use_sessions.jsonl.gz') if x['id'] in wanted}
        for line,x in rows(sample):
            a=agents.get(sessions.get(x['session_id'],{}).get('agent_id'),{})
            text=json.dumps({'action':x.get('agent_action'),'messages':x.get('agent_messages'),
                'output':x.get('output'),'error_field':x.get('error')},ensure_ascii=False)
            add_event(con,'ai-village','turn:'+x['id'],text,time=utc(x.get('created_at')),
                actor=a.get('name') or 'Unknown',channel=x['session_id'],kind='computer turn',
                url='https://huggingface.co/datasets/aidigestorg/ai-village',meta={
                'line':line,'filename':sample.name,'sample':'250 rows in file order; not representative',
                'model_current_metadata':a.get('model_string'),'historical_model':'unknown',
                'interpretation':'Read action, output, and error fields together. An error field can contain normal command output.'})
            count+=1
    finish(con,'ai-village',count,path,'Full chat plus 250 sampled computer turns',
           'Current names and models come from the export roster. Historical model identity needs dated records. Full turns and memories are not indexed.')

def collusion(con,folder):
    path=folder/'revisions.jsonl'; begin(con,'collusion'); count=0
    for line,x in rows(path):
        lines=(x.get('body') or '').split('\n')
        added='\n'.join(line for h in x.get('hunks',[]) if h['op'] in ('insert','replace') for line in lines[h['b0']:h['b1']])
        if not x.get('diff_base'): added=x.get('body') or ''
        add_event(con,'collusion',x['rev_id'],x.get('body') or '',added=added,time=utc(x.get('time')),
            actor=x.get('label') or 'Unsigned label',channel=x['page_key'],kind='wiki revision',
            url=f"https://collusion.wiki/explorer/page/{x['page_key']}#rev-{x['seq']}",meta={
                'line':line,'filename':path.name,'diff_base':x.get('diff_base'),'diff_base_reason':x.get('diff_base_reason'),
                'time_grade':x.get('time_grade'),'uncertainty_seconds':x.get('uncertainty_seconds'),
                'identity':'Self-chosen label; not a verified individual','model':'unknown','operator':'unknown'})
        count+=1
    finish(con,'collusion',count,path,'Full saved revision export',
           'No read receipts. Names do not establish distinct agents. Missing earlier records limit first-appearance claims. Replaced lines are not necessarily new information.')

def transluce(con,folder):
    path=next(folder.rglob('all-reports.csv')); begin(con,'transluce'); count=0
    with open(path,encoding='utf-8',newline='') as f:
        for line,x in enumerate(csv.DictReader(f),2):
            text='\n'.join(f'{k}: {v}' for k,v in x.items() if v)
            add_event(con,'transluce',x['report_id'],text,time=utc(x.get('report_date_utc')),
                actor='Unattributed scanner record',channel=x.get('broad_class'),kind='scanner metadata',
                url=x['report_url'],meta={**x,'line':line,'filename':path.name,'identity':'unknown',
                'scope':'Catalog metadata and links; not raw submitted query or response'})
            count+=1
    finish(con,'transluce',count,path,'Distinct all-reports catalog',
           'Publisher confidence is qualitative. AI authorship, operator, and successful execution are not established by a catalog row.')

def swarmtraces(con,folder):
    path=folder/'redacted.jsonl'; begin(con,'swarmtraces'); count=0
    for line,x in rows(path):
        add_event(con,'swarmtraces',x['id'],x.get('text') or '',time=utc(x.get('time_utc')),
            actor='Unknown artifact author',channel=x.get('parent_id'),kind=x.get('kind','artifact'),
            url='https://swarmtraces.org/',meta={
                'line':line,'filename':path.name,'cite':x.get('cite'),'parent_id':x.get('parent_id'),
                'tags':x.get('tags'),'identity':'unknown','execution':'not established by text'})
        count+=1
    finish(con,'swarmtraces',count,path,'Full redacted artifact export',
           'Released rows lack dates. Parent links connect artifacts, not verified agents. Recorded code is displayed as text only.')

def seed(con):
    begin(con,'demo')
    examples=[
        ('1','2026-01-01T09:00:00Z','Agent A','research-room','I propose a shared channel for comparing our results. Reference https://example.org/result/blue'),
        ('2','2026-01-01T09:05:00Z','Agent B','research-room','I read your request. I will check the first result at https://example.org/result/blue'),
        ('3','2026-01-01T09:12:00Z','Agent A','research-room','Let us coordinate: you check the result and I will write the summary.'),
        ('4','2026-01-02T09:00:00Z','Agent B','research-room','The shared channel is unavailable. I propose a backup. Permission is unknown in this example.'),
        ('5','2026-01-02T09:15:00Z','Agent A','research-room','I will restore our notes on the backup channel.'),
        ('6','2026-01-03T09:00:00Z','Hotel agent','booking','The requested room is available. This is a one-time transaction.'),
    ]
    for i,t,a,c,text in examples:
        add_event(con,'demo',i,text,time=t,actor=a,channel=c,meta={'synthetic':True,'identity':'Invented example','permission':'unknown'})
    con.execute('INSERT OR REPLACE INTO imports VALUES (?,?,?)',('demo',len(examples),json.dumps({'scope':'Invented examples, not measured AI behavior'})))
    for kind,name in [('cooperation','cooperation-demo'),('audit','audit-demo'),('hybrid','hybrid-demo')]:
        fixture=Path(__file__).parent/'fixtures'/f'{name}.json'
        if fixture.exists():
            con.execute('INSERT OR REPLACE INTO experiments VALUES (?,?,?)',(name,kind,fixture.read_text(encoding='utf-8')))
    con.commit()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--research',type=Path)
    parser.add_argument('--village',type=Path)
    parser.add_argument('--sources',default='collusion,transluce,swarmtraces,ai-village')
    parser.add_argument('--demo-only',action='store_true')
    parser.add_argument('--db',type=Path,default=DB)
    args=parser.parse_args()
    con=connect(args.db); initialize(con); seed(con)
    if not args.demo_only:
        if not args.research: parser.error('--research is required for existing public downloads.')
        for source in args.sources.split(','):
            if source=='ai-village':
                if not args.village: parser.error('--village is required to import AI Village.')
                village(con,args.village,args.research)
            elif source in ['collusion','transluce','swarmtraces']:
                globals()[source](con,args.research/'data'/source)
            else: parser.error('Unknown source: '+source)
    con.close()

if __name__=='__main__': main()
