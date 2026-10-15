#!/usr/bin/env python3
"""Aggregate authorized exports locally; emit no query strings or user-level data.

No API credentials, uploads, tracking vendor, scheduler or network dependency.
Search totals are exported-query-row totals, not certified whole-property counts.
"""

import argparse
import csv
from datetime import date, datetime, timezone
import json
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
        if query is None:
            raise ValueError('Search export requires its query dimension')
        clicks, impressions = count(row['clicks']), count(row['impressions'])
        if clicks > impressions:
            raise ValueError('Search clicks cannot exceed impressions')
        result['clicks'] += clicks
        result['impressions'] += impressions
        bucket = 'brand_clicks' if re.search(r'\bfinco[\s-]*pilot\b', query, re.I) else 'nonbrand_clicks'
        result[bucket] += clicks
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--google')
    parser.add_argument('--bing')
    parser.add_argument('--funnel')
    parser.add_argument('--start')
    parser.add_argument('--end')
    args = parser.parse_args()
    try:
        report = build_report(args.start, args.end, args.google, args.bing, args.funnel)
    except (ValueError, OSError, csv.Error):
        parser.exit(2, 'Export validation failed; use documented aggregate columns and interval. No raw rows were emitted.\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
