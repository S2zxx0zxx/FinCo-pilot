import json
import unittest

import growth_indexnow as notify

ORIGIN = 'https://discover.fincopilot.app'
KEY = 'synthetic-test-key-1234'


def page(url, *, robots='index, follow', header=''):
    return (200, {'content-type': 'text/html', 'x-robots-tag': header},
            f'<html><head><link rel="canonical" href="{url}"><meta name="robots" content="{robots}"></head><body><h1>Product guide</h1></body></html>'.encode())


class IndexNowTests(unittest.TestCase):
    def fake(self, overrides=None, post_status=200):
        calls = []
        def request(url, body=None):
            calls.append((url, body))
            if overrides and url in overrides:
                return overrides[url]
            if url == notify.ENDPOINT:
                self.assertEqual(json.loads(body)['host'], 'discover.fincopilot.app')
                return post_status, {}, b''
            if url.endswith('/' + KEY + '.txt'):
                return 200, {'content-type': 'text/plain'}, KEY.encode()
            if url.endswith('/robots.txt'):
                return 200, {'content-type': 'text/plain'}, b'User-agent: *\nAllow: /\n'
            return page(url)
        return calls, request

    def test_default_dry_run_is_offline_and_does_not_echo_key(self):
        def forbidden(*args):
            self.fail('Dry-run must not make any network request')
        result = notify.execute(ORIGIN, ['/features'], KEY, request=forbidden)
        self.assertEqual(result['network_requests'], 0)
        self.assertNotIn(KEY, json.dumps(result))
        self.assertEqual(result['indexed'], 'unknown')

    def test_private_query_cross_host_duplicate_and_invalid_keys_rejected(self):
        for paths in [['/login'], ['/i/token'], ['/?token=x'], ['https://evil.test'], ['/features/'], ['/features', '/features'], []]:
            with self.assertRaises(ValueError):
                notify.prepare_batch(ORIGIN, paths, KEY)
        for origin in ['http://fincopilot.app', 'https://evil.test', ORIGIN + '/', ORIGIN + '?x=1', 'https://fincopilot.app.evil.test', 'https://user:password@fincopilot.app', 'https://127.0.0.1', 'https://fincopilot.app:443']:
            with self.assertRaises(ValueError):
                notify.prepare_batch(origin, ['/'], KEY)
        for key in [None, 'short', 'bad/key/1234', 'a' * 129]:
            with self.assertRaises(ValueError):
                notify.prepare_batch(ORIGIN, ['/'], key)

    def test_explicit_release_approval_precedes_all_network(self):
        calls, request = self.fake()
        with self.assertRaises(ValueError):
            notify.execute(ORIGIN, ['/'], KEY, submit=True, request=request)
        self.assertEqual(calls, [])

    def test_one_bounded_batch_and_no_indexing_claim_for_pending_key(self):
        calls, request = self.fake(post_status=202)
        result = notify.execute(ORIGIN, list(notify.PUBLIC_PATHS), KEY, submit=True, release_approved=True, request=request)
        self.assertEqual(len(calls), 7)
        self.assertEqual(sum(body is not None for _, body in calls), 1)
        self.assertEqual(result['result'], 'received-key-validation-pending')
        self.assertEqual(result['indexed'], 'unknown')
        self.assertNotIn(KEY, json.dumps(result))

    def test_key_robots_noindex_header_canonical_redirect_and_missing_html_fail_closed(self):
        variants = [
            {ORIGIN + '/' + KEY + '.txt': (200, {'content-type': 'text/html'}, KEY.encode())},
            {ORIGIN + '/' + KEY + '.txt': (200, {'content-type': 'text/plain'}, b'wrong-key')},
            {ORIGIN + '/robots.txt': (200, {'content-type': 'text/plain'}, b'User-agent: bingbot\nDisallow: /\n')},
            {ORIGIN + '/features': page(ORIGIN + '/features', robots='noindex, follow')},
            {ORIGIN + '/features': page(ORIGIN + '/features', header='googlebot: noindex')},
            {ORIGIN + '/features': page(ORIGIN + '/wrong')},
            {ORIGIN + '/features': (302, {'location': 'https://evil.test'}, b'')},
            {ORIGIN + '/features': (200, {'content-type': 'text/html'}, b'<h1>Login</h1>')},
        ]
        for overrides in variants:
            with self.subTest(overrides=list(overrides)):
                calls, request = self.fake(overrides)
                with self.assertRaises(ValueError):
                    notify.execute(ORIGIN, ['/features'], KEY, submit=True, release_approved=True, request=request)
                self.assertTrue(all(body is None for _, body in calls))

    def test_no_retry_after_search_engine_failure(self):
        calls, request = self.fake(post_status=429)
        with self.assertRaises(ValueError):
            notify.execute(ORIGIN, ['/features'], KEY, submit=True, release_approved=True, request=request)
        self.assertEqual(len(calls), 4)
        self.assertEqual(sum(body is not None for _, body in calls), 1)

    def test_same_origin_namespace_uses_only_actual_public_welcome_urls(self):
        result = notify.prepare_batch('https://fincopilot.app', ['/', '/features'], KEY, base_path='/welcome')
        self.assertEqual(result['urlList'], ['https://fincopilot.app/welcome/', 'https://fincopilot.app/welcome/features/'])
        self.assertEqual(result['keyLocation'], 'https://fincopilot.app/' + KEY + '.txt')
        for prefix in ['/api', '/i/token', '/welcome?token=x', 'https://evil.test']:
            with self.assertRaises(ValueError):
                notify.prepare_batch(ORIGIN, ['/features'], KEY, base_path=prefix)

    def test_namespace_dry_run_does_not_activate_notifications(self):
        result = notify.execute('https://fincopilot.app', ['/features'], KEY, base_path='/welcome')
        self.assertEqual(result['network_requests'], 0)
        self.assertEqual(result['urls'], ['https://fincopilot.app/welcome/features/'])
        self.assertEqual(result['mode'], 'dry-run')

    def test_redirect_handler_never_creates_redirected_request(self):
        self.assertIsNone(notify.NoRedirects().redirect_request(None, None, 302, '', {}, 'https://evil.test'))


if __name__ == '__main__':
    unittest.main()
