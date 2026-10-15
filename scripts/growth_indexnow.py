#!/usr/bin/env python3
"""Bounded, manual IndexNow notifier. Default is offline dry-run; never scheduled.

Only the four approved public marketing paths are supported. No private URLs,
redirects, retries, credentials, cookies, response-body logs or arbitrary endpoint.
A successful receipt is not proof of crawling, indexing, ranking or growth.
"""

import argparse
from html.parser import HTMLParser
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

PUBLIC_PATHS = ('/', '/features', '/how-it-works', '/guides/import-transactions')
ENDPOINT = 'https://api.indexnow.org/indexnow'
BODY_LIMIT = 256 * 1024


class VerificationError(ValueError):
    pass


def owned_origin(value):
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment
            or value != 'https://' + host or not re.fullmatch(r'[a-z0-9.-]+', host)
            or not (host == 'fincopilot.app' or host.endswith('.fincopilot.app'))
            or any(not label or label.startswith('-') or label.endswith('-') for label in host.split('.'))):
        raise VerificationError('Use one explicit owned HTTPS origin without a trailing slash or other URL components')
    return value


def prepare_batch(origin, paths, key):
    owned_origin(origin)
    if not re.fullmatch(r'[A-Za-z0-9-]{8,128}', key or ''):
        raise VerificationError('A valid IndexNow key must be supplied through FINCO_INDEXNOW_KEY')
    if not paths or len(paths) > len(PUBLIC_PATHS) or len(set(paths)) != len(paths) or any(path not in PUBLIC_PATHS for path in paths):
        raise VerificationError('Choose one to four distinct approved public paths; private/query/token paths are rejected')
    return {'host': urlsplit(origin).hostname, 'key': key,
            'keyLocation': origin + '/' + key + '.txt',
            'urlList': [origin + path for path in paths]}


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def transport(url, body=None):
    headers = {'User-Agent': 'FinCo-Pilot-Release-Check/1.0', 'Accept-Encoding': 'identity'}
    if body is not None:
        headers['Content-Type'] = 'application/json; charset=utf-8'
    request = Request(url, data=body, headers=headers, method='POST' if body is not None else 'GET')
    try:
        with build_opener(NoRedirects()).open(request, timeout=15) as response:
            data = response.read(BODY_LIMIT + 1)
            if len(data) > BODY_LIMIT:
                raise VerificationError('Response exceeded the bounded verification budget')
            return response.status, {k.lower(): v for k, v in response.headers.items()}, data
    except (HTTPError, URLError, OSError) as error:
        # Never echo exception URLs (key location), headers or response bodies.
        raise VerificationError('HTTP verification or submission failed; no retry performed') from None


class PublicHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.robots = []
        self.h1_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'link' and 'canonical' in attrs.get('rel', '').lower().split():
            self.canonicals.append(attrs.get('href', ''))
        if tag == 'meta' and attrs.get('name', '').lower() in ('robots', 'bingbot', 'googlebot'):
            self.robots.append(attrs.get('content', ''))


def excluded(value):
    return bool(re.search(r'\b(?:noindex|none)\b', value, re.I))


def validate_public_page(url, status, headers, body):
    if status != 200 or headers.get('content-type', '').split(';')[0].strip().lower() != 'text/html':
        raise VerificationError('Public marketing page must return initial HTML with HTTP 200')
    if excluded(headers.get('x-robots-tag', '')):
        raise VerificationError('Public page has an indexing exclusion header')
    try:
        parser = PublicHTML()
        parser.feed(body.decode('utf-8'))
    except (UnicodeError, ValueError):
        raise VerificationError('Public HTML could not be validated') from None
    if parser.canonicals != [url] or parser.h1_count != 1 or not parser.robots or any(excluded(v) for v in parser.robots):
        raise VerificationError('Public page requires one exact canonical, one H1 and explicit indexable robots metadata')


def execute(origin, paths, key, *, submit=False, release_approved=False, request=transport):
    batch = prepare_batch(origin, paths, key)
    summary = {'mode': 'dry-run', 'origin': origin, 'urls': batch['urlList'], 'network_requests': 0,
               'key_configured': True, 'indexed': 'unknown',
               'limitation': 'Receipt is not proof of crawling or indexing. No automatic retries or repeated submissions.'}
    if not submit:
        return summary
    if not release_approved:
        raise VerificationError('Submission requires explicit release approval; dry-run remains offline')
    status, headers, body = request(batch['keyLocation'])
    summary['network_requests'] += 1
    if status != 200 or headers.get('content-type', '').split(';')[0].strip().lower() != 'text/plain' or body not in (key.encode(), (key + '\n').encode()):
        raise VerificationError('Root key file must return only the expected UTF-8 text key')
    status, headers, body = request(origin + '/robots.txt')
    summary['network_requests'] += 1
    if status != 200 or headers.get('content-type', '').split(';')[0].strip().lower() != 'text/plain':
        raise VerificationError('A directly accessible plain-text robots policy is required')
    try:
        policy = RobotFileParser()
        policy.parse(body.decode('utf-8').splitlines())
    except UnicodeError:
        raise VerificationError('Robots policy is not valid UTF-8') from None
    for url in batch['urlList']:
        if not policy.can_fetch('bingbot', url):
            raise VerificationError('The current robots policy excludes a submitted URL')
        status, headers, body = request(url)
        summary['network_requests'] += 1
        validate_public_page(url, status, headers, body)
    status, _, _ = request(ENDPOINT, json.dumps(batch).encode('utf-8'))
    summary['network_requests'] += 1
    if status not in (200, 202):
        raise VerificationError('IndexNow did not accept the notification; no retry performed')
    summary.update(mode='submitted', response_status=status,
                   result='received-key-validation-pending' if status == 202 else 'received')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--path', action='append', required=True, dest='paths')
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--release-approved', action='store_true')
    args = parser.parse_args()
    try:
        result = execute(args.origin, args.paths, os.environ.get('FINCO_INDEXNOW_KEY'),
                         submit=args.submit, release_approved=args.release_approved)
    except (VerificationError, ValueError):
        parser.exit(2, 'IndexNow validation failed. Check documented release gates; no raw URLs, keys or response content emitted.\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
