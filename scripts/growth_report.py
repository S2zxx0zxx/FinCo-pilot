#!/usr/bin/env python3
"""Aggregate authorized exports locally; emit no query strings or user-level data.

No API credentials, uploads, tracking vendor, scheduler or network dependency.
Search totals are exported-query-row totals, not certified whole-property counts.
"""

import argparse
import csv
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import re

METRICS = (
    'google_clicks', 'google_impressions', 'google_brand_clicks', 'google_nonbrand_clicks',
    'bing_clicks', 'bing_impressions', 'bing_brand_clicks', 'bing_nonbrand_clicks',
    'organic_visits', 'organic_signups', 'organic_activated', 'signup_conversion_rate',
    'activation_rate', 'observed_ai_citations',
)


def blank_report(start=None, end=None):
    return {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'period': {'start': start, 'end': end},
            'metrics': {name: {'value': None, 'status': 'unknown'} for name in METRICS},
            'limitations': ['Missing data is unknown, not zero.',
                            'Exports are supplied evidence, not independently verified API results.',
                            'Search totals cover exported query rows, which may omit anonymized or truncated data.',
                            'Funnel rows must use a consistent consent-eligible organic signup cohort.']}


def read_rows(path, allowed, required):
    path = Path(path)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('Export exceeds the local size budget')
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        headers = [header.strip().lower() for header in (reader.fieldnames or [])]
        if len(set(headers)) != len(headers) or not set(headers) <= allowed or not required <= set(headers):
            raise ValueError('Unexpected export schema; user-level or financial columns are not accepted')
        reader.fieldnames = headers
        rows = []
        for index, row in enumerate(reader):
            if index >= 100000 or None in row or any(value is None for value in row.values()):
                raise ValueError('Invalid or oversized export')
            rows.append(row)
    if not rows:
        raise ValueError('An empty export does not establish a zero baseline')
    return rows


def count(value):
    if not re.fullmatch(r'\d+', value.strip()):
        raise ValueError('Counts must be explicit nonnegative integers')
    result = int(value)
    if result > 10 ** 12:
        raise ValueError('Count exceeds the reporting budget')
    return result


def search_totals(path):
    rows = read_rows(path, {'query', 'top queries', 'clicks', 'impressions', 'ctr', 'position'}, {'clicks', 'impressions'})
    result = {'clicks': 0, 'impressions': 0, 'brand_clicks': 0, 'nonbrand_clicks': 0}
    for row in rows:
        query = row.get('query', row.get('top queries'))
        if query is None or not query.strip() or ('query' in row and 'top queries' in row):
            raise ValueError('Search export requires one unambiguous nonempty query dimension')
        clicks, impressions = count(row['clicks']), count(row['impressions'])
        if clicks > impressions:
            raise ValueError('Search clicks cannot exceed impressions')
        result['clicks'] += clicks
        result['impressions'] += impressions
        bucket = 'brand_clicks' if re.search(r'\bfinco[\s-]*pilot\b', query, re.I) else 'nonbrand_clicks'
        result[bucket] += clicks
        if any(value > 2 ** 53 - 1 for value in result.values()):
            raise ValueError('Aggregate count exceeds safe reporting precision')
    return result


def funnel_totals(path):
    rows = read_rows(path, {'channel', 'visits', 'signups', 'activated'}, {'channel', 'visits', 'signups', 'activated'})
    totals = {'organic_visits': 0, 'organic_signups': 0, 'organic_activated': 0}
    found = False
    for row in rows:
        if row['channel'] != 'organic_search':
            raise ValueError('Only the explicit aggregate organic_search channel is accepted')
        visits, signups, activated = count(row['visits']), count(row['signups']), count(row['activated'])
        if not activated <= signups <= visits:
            raise ValueError('Use a consistent deduplicated visit/signup/activation cohort')
        found = True
        totals['organic_visits'] += visits
        totals['organic_signups'] += signups
        totals['organic_activated'] += activated
        if any(value > 2 ** 53 - 1 for value in totals.values()):
            raise ValueError('Aggregate count exceeds safe reporting precision')
    if not found:
        raise ValueError('No organic cohort rows')
    totals['signup_conversion_rate'] = totals['organic_signups'] / totals['organic_visits'] if totals['organic_visits'] else None
    totals['activation_rate'] = totals['organic_activated'] / totals['organic_signups'] if totals['organic_signups'] else None
    return totals


def build_report(start=None, end=None, google=None, bing=None, funnel=None):
    if bool(start) != bool(end):
        raise ValueError('Reporting interval requires both dates')
    if start:
        date.fromisoformat(start)
        date.fromisoformat(end)
    if any((google, bing, funnel)) and not (start and end):
        raise ValueError('Authorized exports require an explicit reporting interval')
    if start and end and date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError('Reporting interval is reversed')
    report = blank_report(start, end)
    for source, path in [('google', google), ('bing', bing)]:
        if path:
            for name, value in search_totals(path).items():
                report['metrics'][source + '_' + name] = {'value': value, 'status': 'export-derived'}
    if funnel:
        for name, value in funnel_totals(funnel).items():
            report['metrics'][name] = {'value': value, 'status': 'export-derived' if value is not None else 'unknown'}
    return report


def validated_metrics(report):
    """Accept only this sanitized report schema; never echo arbitrary input fields."""
    if not isinstance(report, dict) or report.get('schema_version') != 1 or not isinstance(report.get('metrics'), dict):
        raise ValueError('Unknown aggregate report schema')
    if not set(report['metrics']) <= set(METRICS):
        raise ValueError('Unknown metric dimension')
    clean = {}
    for name in METRICS:
        metric = report['metrics'].get(name, {'value': None, 'status': 'unknown'})
        if not isinstance(metric, dict) or set(metric) != {'value', 'status'}:
            raise ValueError('Invalid aggregate metric schema')
        value, status = metric['value'], metric['status']
        if status == 'unknown' and value is None:
            clean[name] = metric.copy()
            continue
        if (status != 'export-derived' or isinstance(value, bool) or not isinstance(value, (int, float))
                or value < 0 or value > 2 ** 53 - 1 or not math.isfinite(value)):
            raise ValueError('Invalid measured aggregate value')
        if name.endswith('_rate'):
            if value > 1:
                raise ValueError('Invalid cohort rate')
        elif not isinstance(value, int) or value > 2 ** 53 - 1:
            raise ValueError('Aggregate count must be a safe integer')
        clean[name] = metric.copy()
    for prefix in ('google', 'bing'):
        clicks, impressions, branded, nonbrand = (clean[prefix + '_' + key]['value'] for key in ('clicks', 'impressions', 'brand_clicks', 'nonbrand_clicks'))
        if clicks is not None and impressions is not None and clicks > impressions:
            raise ValueError('Inconsistent aggregate search counts')
        if all(value is not None for value in (clicks, branded, nonbrand)) and branded + nonbrand != clicks:
            raise ValueError('Brand split does not match exported totals')
    visits, signups, activated = (clean[key]['value'] for key in ('organic_visits', 'organic_signups', 'organic_activated'))
    if all(value is not None for value in (visits, signups, activated)) and not activated <= signups <= visits:
        raise ValueError('Inconsistent aggregate organic cohort')
    for name, numerator, denominator in [('signup_conversion_rate', signups, visits), ('activation_rate', activated, signups)]:
        value = clean[name]['value']
        if value is not None and (numerator is None or not denominator or not math.isclose(value, numerator / denominator, abs_tol=1e-12)):
            raise ValueError('Rate does not match its cohort')
    return clean


def interval(report):
    period = report.get('period')
    if not isinstance(period, dict) or set(period) != {'start', 'end'}:
        raise ValueError('Explicit reporting dates are required')
    start, end = period['start'], period['end']
    if not all(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) for value in (start, end)):
        raise ValueError('Explicit ISO reporting dates are required')
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError('Reporting interval is reversed')
    return first, last, (last - first).days + 1


def compare_reports(current, previous, *, cohorts_confirmed=False):
    current_metrics, previous_metrics = validated_metrics(current), validated_metrics(previous)
    current_start, current_end, current_days = interval(current)
    previous_start, previous_end, previous_days = interval(previous)
    reasons = []
    if not cohorts_confirmed:
        reasons.append('Consent, source definitions and deduplicated cohort comparability have not been confirmed.')
    if previous_end >= current_start:
        reasons.append('Periods overlap or are not in chronological order.')
    if current_days != previous_days:
        reasons.append('Count windows have unequal durations; choose matched windows before comparing totals.')
    result = {'status': 'not-comparable' if reasons else 'comparable-by-supplied-contract',
              'current_period': {'start': current_start.isoformat(), 'end': current_end.isoformat()},
              'previous_period': {'start': previous_start.isoformat(), 'end': previous_end.isoformat()},
              'reasons': reasons, 'metrics': {},
              'limitations': ['Comparability confirmation is supplied by the operator, not independent verification.',
                              'Period changes are descriptive and do not establish causal uplift.',
                              'Missing metrics remain unknown; a zero baseline has no defined percentage change.']}
    for name in METRICS:
        current_value, previous_value = current_metrics[name]['value'], previous_metrics[name]['value']
        observed = not reasons and current_value is not None and previous_value is not None
        delta = current_value - previous_value if observed else None
        result['metrics'][name] = {'current': current_value, 'previous': previous_value,
            'absolute_change': delta,
            'relative_change': delta / previous_value if observed and previous_value else None,
            'percentage_point_change': delta * 100 if observed and name.endswith('_rate') else None,
            'status': 'export-derived' if observed else 'unknown'}
    return result


def read_report(path):
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Sanitized report exceeds size limit')
    report = json.loads(path.read_text(encoding='utf-8'))
    validated_metrics(report)
    interval(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--google')
    parser.add_argument('--bing')
    parser.add_argument('--funnel')
    parser.add_argument('--start')
    parser.add_argument('--end')
    parser.add_argument('--previous', help='Local sanitized report for a previous matched interval')
    parser.add_argument('--comparable-cohorts', action='store_true', help='Operator confirms unchanged consent/source/cohort definitions')
    args = parser.parse_args()
    try:
        report = build_report(args.start, args.end, args.google, args.bing, args.funnel)
        if args.previous:
            report['comparison'] = compare_reports(report, read_report(args.previous), cohorts_confirmed=args.comparable_cohorts)
        elif args.comparable_cohorts:
            raise ValueError('Comparability confirmation requires a previous report')
    except (ValueError, OSError, csv.Error, TypeError):
        parser.exit(2, 'Export validation failed; use documented aggregate columns and interval. No raw rows were emitted.\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
