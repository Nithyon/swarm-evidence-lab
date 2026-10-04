"""Relationships supported by records. No inferred owners, reads, or causality."""
import hashlib
import json
from urllib.parse import urlparse
import lab


def record_graph(con, query='', source='', limit=30, keys=None):
    if keys:
        rows = con.execute('SELECT * FROM events WHERE key IN (' + ','.join('?' for _ in keys) + ') ORDER BY time IS NULL,time,key',keys).fetchall()
        result = {'events': [lab.unpack(row) for row in rows], 'total': len(rows)}
    else:
        result = lab.find_events(con, query[:500], source, limit=min(60, max(1, limit)))
    nodes, edges, references = {}, [], {}
    for record in result['events']:
        key = record['key']
        # Generic human/scanner labels cannot identify an individual across records.
        label = record.get('actor') or 'Unattributed record'
        unidentified = record['meta'].get('speaker_type') == 'human' or label.lower() in ['human', 'user', 'unattributed scanner record']
        actor = 'label:' + (key if unidentified else record['source'] + ':' + label)
        nodes.setdefault(actor, {'id': actor, 'type': 'label', 'label': label,
                                 'note': 'Recorded label. Operator and historical model are unverified.'})
        nodes[key] = {'id': key, 'type': 'action' if 'computer' in record['kind'] or 'tool' in record['kind'] else 'record',
                      'label': record['record_id'], 'record': record,
                      'note': 'Recorded tool activity does not establish successful execution.'}
        edges.append({'from': actor, 'to': key, 'kind': 'recorded label', 'record_key': key})
        for ref in con.execute('SELECT url,status FROM links WHERE event_key=? ORDER BY url LIMIT 8', (key,)):
            target = 'url:' + hashlib.sha256(ref['url'].encode()).hexdigest()[:20]
            nodes.setdefault(target, {'id': target, 'type': 'reference', 'label': urlparse(ref['url']).netloc,
                                      'url': ref['url'], 'note': 'Exact URL reference, not a read receipt.'})
            edges.append({'from': key, 'to': target, 'kind': ref['status'], 'record_key': key})
            references.setdefault(ref['url'], []).append({'key': key, 'status': ref['status']})
    # A diff base is a revision relationship, not communication between the authors.
    for record in result['events']:
        parent = record['meta'].get('diff_base')
        if parent in nodes:
            edges.append({'from': parent, 'to': record['key'], 'kind': 'revision of', 'record_key': record['key']})
    shared = [{'url': url, 'records': len(refs), 'inherited': sum('inherited' in r['status'] for r in refs)}
              for url, refs in references.items() if len(refs) > 1]
    return {'nodes': list(nodes.values()), 'edges': edges, 'records': result['events'],
            'total': result['total'], 'shown': len(result['events']), 'shared': shared,
            'title': 'Follow a reference', 'description': 'Recorded labels, source records, and exact URLs.',
            'scope': 'First matching records in available date order. At most eight URLs per record.',
            'limits': 'Edges do not establish reads, causal influence, independent operators, permission, or collusion.'}


def board_case():
    return json.loads((lab.ROOT / 'fixtures' / 'board-graph.json').read_text(encoding='utf-8'))


def village_case(con):
    keys=['ai-village:'+key for key in ['4ea9ffab-684b-4080-a3ed-6a089aed2904','1474d860-b039-458d-8ac8-3433f2d096aa','24f24536-20ea-4753-af35-c5609749cb53','b3e534cd-a3ab-4bcb-9bff-df23d283e5dc','7de4a6cd-71e5-4cad-bade-4665ebbe0dab']]
    graph=record_graph(con,keys=keys)
    graph.update(title='The shared document is ready. What shows it?',description='A human proposes a shared document. The recorded agent plans it, then claims it is shared.',scope='Five selected AI Village chat records from June 4, 2025. Full tool records have not been checked for this case.')
    return graph
