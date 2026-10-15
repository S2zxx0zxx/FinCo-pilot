import json
from pathlib import Path
import tempfile
import unittest

import growth_report as report


class ReportingTests(unittest.TestCase):
    def fixture(self, text):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'export.csv'
        path.write_text(text)
        return path

    def test_missing_data_is_unknown_not_zero(self):
        result = report.build_report()
        self.assertEqual(len(result['metrics']), 14)
        self.assertTrue(all(value['value'] is None for value in result['metrics'].values()))

    def test_search_aggregates_without_copying_raw_queries_or_paths(self):
        path = self.fixture('Top queries,Clicks,Impressions,CTR,Position\nfinco-pilot,2,10,20%,1\nprivate account text,3,30,10%,5\n')
        result = report.build_report('2026-10-01', '2026-10-14', google=path)
        self.assertEqual(result['metrics']['google_clicks']['value'], 5)
        self.assertEqual(result['metrics']['google_brand_clicks']['value'], 2)
        self.assertNotIn('private account', json.dumps(result))
        self.assertNotIn(str(path), json.dumps(result))

    def test_unexpected_financial_or_identity_headers_rejected(self):
        for header in ['email', 'balance', 'token']:
            path = self.fixture(f'query,clicks,impressions,{header}\nfinco-pilot,1,2,private\n')
            with self.assertRaises(ValueError):
                report.search_totals(path)

    def test_cohort_rates_do_not_use_search_impressions_as_visits(self):
        path = self.fixture('channel,visits,signups,activated\norganic_search,100,10,4\n')
        result = report.build_report('2026-10-01', '2026-10-14', funnel=path)
        self.assertEqual(result['metrics']['signup_conversion_rate']['value'], .1)
        self.assertEqual(result['metrics']['activation_rate']['value'], .4)
        self.assertIsNone(result['metrics']['google_impressions']['value'])

    def test_bad_or_empty_counts_and_inconsistent_cohorts_are_rejected(self):
        for text in ['query,clicks,impressions\n', 'query,clicks,impressions\nx,-1,2\n',
                     'query,clicks,impressions\nx,3,2\n', 'query,clicks,impressions\nx,,2\n', 'query,clicks,impressions\n,1,2\n',
                     'query,top queries,clicks,impressions\nx,y,1,2\n']:
            with self.assertRaises(ValueError):
                report.search_totals(self.fixture(text))
        with self.assertRaises(ValueError):
            report.funnel_totals(self.fixture('channel,visits,signups,activated\norganic_search,3,4,1\n'))
        with self.assertRaises(ValueError):
            report.build_report('2026-10-15', '2026-10-01')
        with self.assertRaises(ValueError):
            report.build_report(google=self.fixture('query,clicks,impressions\nx,1,2\n'))
        for start, end in [('2026-10-01', None), (None, '2026-10-14'), ('2026-02-30', '2026-03-01')]:
            with self.assertRaises(ValueError):
                report.build_report(start, end)


if __name__ == '__main__':
    unittest.main()
