import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from api.index import handler


class HostedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self,path,body=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        request=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with urllib.request.urlopen(request) as response:return json.load(response)

    def test_hosted_data_is_synthetic_only(self):
        self.assertTrue(self.request('/api/session')['hosted'])
        summary=self.request('/api/summary')
        self.assertEqual(summary['total'],6)
        self.assertTrue(all(x['n']==0 for x in summary['datasets'] if x['id']!='demo'))
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/event?key=ai-village:private-record')
        self.assertEqual(error.exception.code,404)

    def test_review_validation_does_not_share_or_persist_work(self):
        body={'title':'Visitor one','records':['demo:1'],'judgments':{},'reason':'Synthetic example.'}
        saved=self.request('/api/review/check',body)
        self.assertEqual(saved['title'],'Visitor one')
        self.assertEqual(self.request('/api/summary')['reviews'],0)
        report=self.request('/api/report/render',body)['text']
        self.assertIn('demo / 1',report)
        self.assertNotIn('I propose a shared channel',report)

    def test_public_graph_has_invented_records_without_private_data(self):
        graph=self.request('/api/graph?case=example')
        self.assertTrue(graph['synthetic'])
        self.assertEqual(graph['shown'],3)
        self.assertTrue(all(r['meta']['synthetic'] and r['source']=='synthetic-example' for r in graph['records']))
        self.assertEqual(self.request('/api/graph?source=ai-village')['shown'],0)

    def test_stateless_calculations_use_the_same_method(self):
        examples=self.request('/api/examples')
        for kind in ['cooperation','hybrid','audit']:
            calculated=self.request('/api/calculate',{'kind':kind,'records':examples[kind]['records']})
            baseline=self.request('/api/'+kind)
            baseline.pop('dataset')
            self.assertEqual(calculated,baseline)

    def test_cross_origin_submission_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request('/api/review/check',{},origin='https://outside.example')
        self.assertEqual(error.exception.code,403)

    def test_shared_write_and_unknown_routes_are_unavailable(self):
        for path,body in [('/api/reviews',{}),('/api/experiments',{}),('/api/missing',None)]:
            with self.assertRaises(urllib.error.HTTPError) as error:self.request(path,body)
            self.assertEqual(error.exception.code,404)


if __name__=='__main__':unittest.main()
