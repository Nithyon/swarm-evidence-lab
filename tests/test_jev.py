import copy
import json
import os
import unittest
from unittest.mock import patch
import jev_triage as j

class JevTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'key':'demo:1','source':'demo','kind':'message','time':'2026-01-01T00:00:00Z',
            'actor':'A','text':'I propose a joint check.','added':'I propose a joint check.','meta':'{}'}]
        self.env={'SWARM_JEV_ENABLED':'1','SWARM_JEV_API_KEY':'unit-test-only'}
    def response(self):
        answers={}
        for k,q in j.QUESTIONS.items():
            options=list(q['criteria']);selected=options[-1]
            answers[k]={'type':'choice','choice':selected,'confidence':.7,
                'probabilities':{v:1.0 if v==selected else 0.0 for v in options}}
        return {'model':'jev-test-model','answers':answers,'usage':{'input_tokens':300,'output_tokens':50}}
    def test_disabled_does_not_send(self):
        with patch.dict(os.environ,{},clear=True):
            result=j.decide(self.rows,send=lambda *args:self.fail('Network must not run'))
        self.assertEqual(result['status'],'disabled')
        self.assertIsNone(result['answers']);self.assertFalse(result['provider_called'])
    def test_other_project_settings_do_not_enable_this_adapter(self):
        with patch.dict(os.environ,{'TYPESAFE_API_KEY':'different-project-key','GATE_JEV':'1'},clear=True):
            self.assertFalse(j.status()['ready'])
    def test_enabled_requires_request_permission(self):
        with patch.dict(os.environ,self.env,clear=True):
            with self.assertRaises(ValueError):j.decide(self.rows)
    def test_typed_response_and_usage_preserved(self):
        received=[]
        def send(payload,key,timeout):
            received.append(payload);self.assertEqual(key,'unit-test-only');self.assertEqual(timeout,3)
            return self.response()
        with patch.dict(os.environ,self.env,clear=True):out=j.decide(self.rows,True,send)
        self.assertEqual(out['status'],'ok');self.assertEqual(out['model'],'jev-test-model')
        self.assertEqual(out['usage']['input_tokens'],300)
        self.assertEqual(set(received[0]['questions']),set(j.QUESTIONS))
        self.assertTrue(out['manual_review_required'])
        self.assertNotIn('unit-test-only',json.dumps(out))
    def test_timeout_returns_manual_review_without_fake_probabilities(self):
        def send(*args):raise TimeoutError('private detail should not be exposed')
        with patch.dict(os.environ,self.env,clear=True):out=j.decide(self.rows,True,send)
        self.assertEqual(out['status'],'unavailable');self.assertIsNone(out['answers'])
        self.assertNotIn('private detail',out['message'])
    def test_missing_or_nonfinite_probabilities_rejected(self):
        for missing in [True,False]:
            response=self.response();p=response['answers']['shared_plan']['probabilities']
            if missing:p.pop(next(iter(p)))
            else:p[next(iter(p))]=float('nan')
            with self.assertRaises(ValueError):j.validated_answers(response)
    def test_wrong_choice_and_distribution_total_rejected(self):
        response=self.response();response['answers']['shared_plan']['choice']='proposal'
        with self.assertRaises(ValueError):j.validated_answers(response)
        response=self.response();response['answers']['shared_plan']['probabilities']['unclear']=.2
        with self.assertRaises(ValueError):j.validated_answers(response)
    def test_preview_bounds_and_truncation(self):
        rows=copy.deepcopy(self.rows);rows[0]['text']='a'*10000
        p=j.preview(rows);self.assertEqual(len(p['state']['records'][0]['text']),6000)
        self.assertTrue(p['state']['records'][0]['text_truncated'])
        with self.assertRaises(ValueError):j.preview(rows*13)
        with self.assertRaises(ValueError):j.preview(rows*5)
    def test_snapshot_hash_changes_with_context(self):
        with patch.dict(os.environ,{},clear=True):
            original=j.decide(self.rows)['request_sha256']
            self.rows[0]['text']='A different source claim.'
            self.assertNotEqual(original,j.decide(self.rows)['request_sha256'])
