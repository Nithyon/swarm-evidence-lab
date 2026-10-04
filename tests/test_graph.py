import unittest
import lab
import knowledge_graph as kg


class GraphTests(unittest.TestCase):
    def test_inherited_link_is_not_new_communication(self):
        with lab.connect(':memory:') as con:
            lab.initialize(con)
            first=lab.add_event(con,'collusion','page@1','https://example.org/a',actor='A')
            lab.add_event(con,'collusion','page@2','https://example.org/a',added='Changed heading',actor='B',meta={'diff_base':first})
            graph=kg.record_graph(con,'https://example.org/a')
            self.assertEqual(graph['shared'][0]['inherited'],1)
            self.assertTrue(any(e['kind']=='inherited reference' for e in graph['edges']))
            self.assertTrue(any(e['kind']=='revision of' for e in graph['edges']))
            self.assertFalse(any(e['kind'] in ['influence','read','collusion'] for e in graph['edges']))

    def test_generic_humans_are_not_merged_into_one_person(self):
        with lab.connect(':memory:') as con:
            lab.initialize(con)
            for i in range(2):lab.add_event(con,'ai-village',i,'Shared reference',actor='Human',meta={'speaker_type':'human'})
            graph=kg.record_graph(con,'Shared reference')
            self.assertEqual(len([n for n in graph['nodes'] if n['type']=='label']),2)

    def test_graph_has_bounded_records_and_unknown_dates(self):
        with lab.connect(':memory:') as con:
            lab.initialize(con)
            for i in range(4):lab.add_event(con,'demo',i,'example',actor='Agent')
            graph=kg.record_graph(con,'example',limit=2)
            self.assertEqual((graph['total'],graph['shown']),(4,2))
            self.assertTrue(all(r['time'] is None for r in graph['records']))

    def test_completion_example_is_explicitly_synthetic(self):
        graph=kg.completion_case()
        self.assertTrue(graph['synthetic'])
        self.assertEqual(len(graph['records']),3)
        self.assertTrue(all(r['meta']['synthetic'] and not r['url'] for r in graph['records']))
        self.assertIn('no proof of completion',graph['limits'])
