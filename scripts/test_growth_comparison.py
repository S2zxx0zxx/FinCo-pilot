import copy
import json
import unittest

from growth_report import blank_report, compare_reports, validated_metrics


class ComparisonTests(unittest.TestCase):
    def reports(self):
        previous = blank_report('2026-09-01', '2026-09-14')
        current = blank_report('2026-10-01', '2026-10-14')
        for report, clicks in [(previous, 10), (current, 15)]:
            report['metrics']['google_clicks'] = {'value': clicks, 'status': 'export-derived'}
        return current, previous

    def test_unknown_default_and_unconfirmed_cohorts_do_not_produce_uplift(self):
        current, previous = self.reports()
        result = compare_reports(current, previous)
        self.assertEqual(result['status'], 'not-comparable')
        self.assertIsNone(result['metrics']['google_clicks']['relative_change'])
        self.assertIsNone(result['metrics']['organic_activated']['absolute_change'])

    def test_confirmed_equal_windows_produce_descriptive_counts_without_raw_fields(self):
        current, previous = self.reports()
        current['private_raw_input'] = 'do-not-echo'
        result = compare_reports(current, previous, cohorts_confirmed=True)
        self.assertEqual(result['metrics']['google_clicks']['absolute_change'], 5)
        self.assertEqual(result['metrics']['google_clicks']['relative_change'], .5)
        self.assertNotIn('do-not-echo', json.dumps(result))
        self.assertIsNone(result['metrics']['observed_ai_citations']['absolute_change'])

    def test_zero_baseline_has_no_percentage_change(self):
        current, previous = self.reports()
        previous['metrics']['google_clicks']['value'] = 0
        result = compare_reports(current, previous, cohorts_confirmed=True)
        self.assertEqual(result['metrics']['google_clicks']['absolute_change'], 15)
        self.assertIsNone(result['metrics']['google_clicks']['relative_change'])

    def test_unequal_or_overlapping_periods_block_changes_and_bad_dates_reject(self):
        current, previous = self.reports()
        for period in [{'start': '2026-10-02', 'end': '2026-10-14'}, {'start': '2026-09-01', 'end': '2026-09-14'}]:
            other = copy.deepcopy(current)
            other['period'] = period
            result = compare_reports(other, previous, cohorts_confirmed=True)
            self.assertEqual(result['status'], 'not-comparable')
            self.assertIsNone(result['metrics']['google_clicks']['absolute_change'])
        current['period']['start'] = '2026-02-30'
        with self.assertRaises(ValueError):
            compare_reports(current, previous, cohorts_confirmed=True)

    def test_rate_changes_use_percentage_points_and_actual_cohort_denominators(self):
        current, previous = self.reports()
        for report, signups in [(current, 20), (previous, 10)]:
            for key, value in [('organic_visits', 100), ('organic_signups', signups), ('organic_activated', 5), ('signup_conversion_rate', signups / 100), ('activation_rate', 5 / signups)]:
                report['metrics'][key] = {'value': value, 'status': 'export-derived'}
        result = compare_reports(current, previous, cohorts_confirmed=True)
        self.assertAlmostEqual(result['metrics']['signup_conversion_rate']['percentage_point_change'], 10)
        current['metrics']['signup_conversion_rate']['value'] = .99
        with self.assertRaises(ValueError):
            validated_metrics(current)

    def test_invalid_or_inconsistent_metrics_rejected(self):
        current, previous = self.reports()
        for metric in [{'value': True, 'status': 'export-derived'}, {'value': float('nan'), 'status': 'export-derived'}, {'value': 10 ** 400, 'status': 'export-derived'}, {'value': 1, 'status': 'unknown'}, {'value': 3.5, 'status': 'export-derived'}, {'value': None, 'status': 'export-derived'}]:
            bad = copy.deepcopy(current)
            bad['metrics']['google_clicks'] = metric
            with self.assertRaises(ValueError):
                compare_reports(bad, previous, cohorts_confirmed=True)
        current['metrics']['google_impressions'] = {'value': 1, 'status': 'export-derived'}
        with self.assertRaises(ValueError):
            validated_metrics(current)


if __name__ == '__main__':
    unittest.main()
