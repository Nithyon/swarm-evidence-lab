import datetime as dt
import tempfile
import unittest
from pathlib import Path
import lab
import swarm_metrics as m

class ActivityTests(unittest.TestCase):
    def test_missing_dates_and_prior_only_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            with lab.connect(Path(temp)/'activity.sqlite') as con:
                lab.initialize(con)
                for day in range(1,10):
                    for i in range(20 if day==9 else 2):
                        lab.add_event(con,'demo',f'{day}-{i}','test',time=f'2026-01-{day:02d}T00:00:00Z')
                lab.add_event(con,'demo','missing','test')
                con.commit()
                out=lab.activity(con,'demo')
                self.assertEqual(out['missing_dates'],1)
                self.assertEqual(out['dated_records'],36)
                self.assertEqual(out['bins'][-1]['expected_count'],2)
                self.assertTrue(out['bins'][-1]['burst'])
                self.assertIsNone(out['bins'][0]['expected_count'])
    def test_inherited_and_unattributed_mentions_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            with lab.connect(Path(temp)/'trace.sqlite') as con:
                lab.initialize(con)
                for source,rid,actor,added in [('collusion','1','A',None),('collusion','2','B','new comment'),('transluce','3','unknown',None)]:
                    lab.add_event(con,source,rid,'https://example.org/a',time=f'2026-01-0{rid}T00:00:00Z',actor=actor,
                        added=added,meta={'diff_base':'1'} if rid=='2' else {})
                con.commit()
                patterns=lab.trace(con,'https://example.org/a')['mention_patterns']
                self.assertEqual(patterns['eligible_records'],1)
                self.assertEqual(patterns['excluded_records'],2)
                self.assertIsNone(patterns['median_first_mention_delay_seconds'])
    def test_module_bin_gaps_timezone_and_ties(self):
        self.assertEqual(m.bin_activity(['2026-01-01','2026-01-03']).counts,(1,0,1))
        t=m.parse_timestamp('2026-01-01T01:00:00+01:00')
        self.assertEqual(t.hour,0)
        tied=[m.ActivityEvent(t,'s',a,('url',)) for a in ['A','B']]
        self.assertEqual(list(m.artifact_interactions(tied)),[])
        self.assertIsNone(m.compute_infection_latency(tied).median_latency_seconds)
    def test_descriptive_reciprocity_is_order_based(self):
        t=m.parse_timestamp('2026-01-01')
        rows=[m.ActivityEvent(t+dt.timedelta(seconds=i),'s',a,('url',)) for i,a in enumerate(['A','B','A'])]
        self.assertEqual(m.compute_reciprocity(m.artifact_interactions(rows)).edge_reciprocity,1)
        self.assertEqual(m.compute_infection_latency(rows).median_latency_seconds,1)
