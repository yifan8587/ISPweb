#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验浏览器与网关使用同一套混淆算法，并检查网关会拒绝未签名请求。"""

from __future__ import annotations

import http.client
import json
import os
import pathlib
import socket
import ssl
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy' / 'gate'))
sys.path.insert(0, str(ROOT / 'deploy' / 'lib'))

from render_nginx import build_replacements, render_text  # noqa: E402
from urlguard_crypto import GuardError, build_guarded, open_request, NonceCache  # noqa: E402
from urlguard_gate import Config, GuardServer, check_edge  # noqa: E402


DOMAIN = 'portal.example.com'
SECRET = 'unit-test-secret'


def free_port() -> int:
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class UpstreamHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _handle(self):
        length = int(self.headers.get('Content-Length', '0') or 0)
        body = self.rfile.read(length) if length else b''
        self.server.seen.append((
            self.command,
            self.path,
            body,
            self.headers.get('X-ISP-Portal-Key'),
        ))
        payload = b'{"ok":true}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def log_message(self, fmt, *args):
        return


class UrlGuardTests(unittest.TestCase):
    def test_browser_and_python_match(self):
        cases = [
            ('GET', '/api/portal/products/', 'page=1', '', 'http'),
            ('POST', '/api/auth/token/', '', '{"username":"a"}', 'http'),
            ('GET', '/ws/resource/vnc/9/', 'token=abc&port=1', '', 'ws'),
            ('GET', '/api/portal/products/', 'q=%E4%B8%AD%E6%96%87', '', 'http'),
        ]
        for method, path, query, body, channel in cases:
            with self.subTest(path=path, channel=channel):
                timestamp = '1700000000'
                nonce = '0123456789abcdef0123456789abcdef'
                python_result = build_guarded(
                    SECRET, method, path, query, body.encode(), channel, timestamp, nonce,
                )
                completed = subprocess.run(
                    [
                        'node', str(ROOT / 'deploy' / 'test' / 'check_urlguard.mjs'),
                        SECRET, method, path, query, body, timestamp, nonce, channel,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                browser = json.loads(completed.stdout)
                self.assertEqual(browser['url'], python_result['url'])
                self.assertEqual(browser['bodyHash'], python_result['body_hash'])

    def test_rejects_bad_signature_and_replay(self):
        cache = NonceCache()
        now = int(time.time())
        nonce = 'abcdef0123456789abcdef0123456789'
        built = build_guarded(
            SECRET, 'GET', '/api/portal/products/', 'page=1', b'', 'http', now, nonce,
        )
        path, _, query = built['url'].partition('?')
        opened = open_request('GET', path, query, b'', SECRET, 120, cache)
        self.assertEqual(opened['path'], '/api/portal/products/')
        self.assertEqual(opened['query'], 'page=1')
        with self.assertRaises(GuardError) as replay:
            open_request('GET', path, query, b'', SECRET, 120, cache)
        self.assertEqual(replay.exception.code, 'replay')
        broken = built['url'][:-1] + ('a' if built['url'][-1] != 'a' else 'b')
        bad_path, _, bad_query = broken.partition('?')
        with self.assertRaises(GuardError) as bad:
            open_request('GET', bad_path, bad_query, b'', SECRET, 120, NonceCache())
        self.assertEqual(bad.exception.code, 'bad_hash')

    def test_gateway_proxies_and_hides_plain_api(self):
        upstream = ThreadingHTTPServer(('127.0.0.1', 0), UpstreamHandler)
        upstream.seen = []
        upstream_thread = threading.Thread(target=upstream.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        upstream_thread.start()
        upstream_port = upstream.server_address[1]
        gate_port = free_port()
        os.environ.update({
            'URL_GUARD_SECRET': SECRET,
            'DOMAIN': DOMAIN,
            'API_UPSTREAM': f'http://127.0.0.1:{upstream_port}',
            'URL_GUARD_BIND': '127.0.0.1',
            'URL_GUARD_PORT': str(gate_port),
            'URL_GUARD_STRICT': '1',
            'URL_GUARD_SKEW': '120',
            'PORTAL_API_SECRET': 'unit-test-portal-api-secret-32b!!',
            'URL_GUARD_TLS_NAME': '',
            'URL_GUARD_CA_FILE': '',
            'URL_GUARD_TLS_VERIFY': '1',
        })
        gate = GuardServer(('127.0.0.1', gate_port), Config())
        gate_thread = threading.Thread(target=gate.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        gate_thread.start()
        try:
            time.sleep(0.1)
            built = build_guarded(SECRET, 'GET', '/api/portal/products/', 'page=2', b'')
            status, _ = self.request(gate_port, 'GET', built['url'])
            self.assertEqual(status, 200)
            self.assertEqual(upstream.seen[-1][0], 'GET')
            self.assertEqual(upstream.seen[-1][1], '/api/portal/products/?page=2')

            body = b'{"refresh":"abc"}'
            posted = build_guarded(SECRET, 'POST', '/api/auth/token/refresh/', '', body)
            status, _ = self.request(
                gate_port, 'POST', posted['url'], body, {'Content-Type': 'application/json'},
            )
            self.assertEqual(status, 200)
            self.assertEqual(upstream.seen[-1][1], '/api/auth/token/refresh/')
            self.assertEqual(upstream.seen[-1][2], body)
            self.assertEqual(upstream.seen[-1][3], 'unit-test-portal-api-secret-32b!!')
            blocked = build_guarded(SECRET, 'GET', '/api/system/settings/', '', b'')
            status, _ = self.request(gate_port, 'GET', blocked['url'])
            self.assertEqual(status, 404)

            status, _ = self.request(gate_port, 'GET', built['url'])
            self.assertEqual(status, 404)
            status, _ = self.request(gate_port, 'GET', '/api/portal/products/')
            self.assertEqual(status, 404)
        finally:
            gate.shutdown()
            gate.server_close()
            upstream.shutdown()
            upstream.server_close()

    def test_websocket_rewrites_to_plain_upstream(self):
        seen = {}
        ready = threading.Event()

        def serve():
            server = socket.socket()
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('127.0.0.1', 0))
            server.listen(1)
            seen['port'] = server.getsockname()[1]
            ready.set()
            conn, _ = server.accept()
            conn.settimeout(5)
            data = b''
            while b'\r\n\r\n' not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            seen['request'] = data
            conn.sendall(
                b'HTTP/1.1 101 Switching Protocols\r\n'
                b'Upgrade: websocket\r\n'
                b'Connection: Upgrade\r\n'
                b'\r\nhello'
            )
            seen['echo'] = conn.recv(32)
            conn.close()
            server.close()

        threading.Thread(target=serve, daemon=True).start()
        self.assertTrue(ready.wait(2))
        gate_port = free_port()
        os.environ.update({
            'URL_GUARD_SECRET': SECRET,
            'DOMAIN': DOMAIN,
            'API_UPSTREAM': f'http://127.0.0.1:{seen["port"]}',
            'URL_GUARD_BIND': '127.0.0.1',
            'URL_GUARD_PORT': str(gate_port),
            'URL_GUARD_STRICT': '1',
            'URL_GUARD_TLS_NAME': '',
            'URL_GUARD_CA_FILE': '',
            'URL_GUARD_TLS_VERIFY': '1',
        })
        gate = GuardServer(('127.0.0.1', gate_port), Config())
        threading.Thread(target=gate.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True).start()
        time.sleep(0.1)
        built = build_guarded(SECRET, 'GET', '/ws/resource/vnc/7/', 'token=abc', b'', 'ws')
        request = (
            f'GET {built["url"]} HTTP/1.1\r\n'
            'Host: portal.example.com\r\n'
            'X-Forwarded-Host: portal.example.com\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n'
            'Sec-WebSocket-Version: 13\r\n'
            'Sec-WebSocket-Protocol: binary\r\n'
            '\r\n'
        ).encode()
        client = socket.create_connection(('127.0.0.1', gate_port), timeout=5)
        client.settimeout(5)
        client.sendall(request)
        buffered = b''
        while b'\r\n\r\n' not in buffered:
            buffered += client.recv(4096)
        self.assertIn(b' 101 ', buffered.split(b'\r\n', 1)[0])
        client.sendall(b'Z')
        if b'hello' not in buffered:
            buffered += client.recv(16)
        client.close()
        gate.shutdown()
        gate.server_close()
        self.assertIn(b'GET /ws/resource/vnc/7/?token=abc HTTP/1.1', seen['request'])
        self.assertIn(b'Sec-WebSocket-Protocol: binary', seen['request'])
        self.assertEqual(seen['echo'], b'Z')
        self.assertIn(b'hello', buffered)

    def request(self, port, method, target, body=None, extra=None):
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        headers = {
            'X-Forwarded-Host': DOMAIN,
            'X-Real-IP': '203.0.113.10',
            'Host': DOMAIN,
        }
        if extra:
            headers.update(extra)
        conn.request(method, target, body=body, headers=headers)
        resp = conn.getresponse()
        payload = resp.read()
        conn.close()
        return resp.status, payload


class UpstreamTrustTests(unittest.TestCase):
    def test_ip_upstream_uses_certificate_dns_name(self):
        import subprocess
        import tempfile
        from pathlib import Path

        from upstream_trust import cert_names, choose_tls_name, fetch_peer_pem, trusted

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cert = str(Path(tmp.name) / 'cert.pem')
        key = str(Path(tmp.name) / 'key.pem')
        subprocess.run(
            [
                'openssl', 'req', '-x509', '-nodes', '-newkey', 'rsa:2048',
                '-keyout', key, '-out', cert, '-days', '2',
                '-subj', '/CN=manager.example.com',
                '-addext', 'subjectAltName=DNS:manager.example.com,IP:127.0.0.1',
            ],
            check=True, capture_output=True,
        )

        class HostHandler(UpstreamHandler):
            def _handle(self):
                self.server.seen.append(self.headers.get('Host'))
                super()._handle()

        upstream = ThreadingHTTPServer(('127.0.0.1', 0), HostHandler)
        upstream.seen = []
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        upstream.socket = context.wrap_socket(upstream.socket, server_side=True)
        threading.Thread(target=upstream.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True).start()
        port = upstream.server_address[1]
        self.addCleanup(upstream.shutdown)
        self.addCleanup(upstream.server_close)

        pem = fetch_peer_pem('127.0.0.1', port)
        dns, ips = cert_names(pem)
        self.assertIn('manager.example.com', dns)
        self.assertIn('127.0.0.1', ips)
        self.assertEqual(choose_tls_name('123.253.225.92', dns), 'manager.example.com')
        self.assertEqual(choose_tls_name('manager.example.com', dns), '')
        self.assertFalse(trusted('127.0.0.1', port, 'manager.example.com')[0])
        self.assertTrue(trusted('127.0.0.1', port, 'manager.example.com', cert)[0])

        gate_port = free_port()
        os.environ.update({
            'URL_GUARD_SECRET': SECRET,
            'DOMAIN': DOMAIN,
            'API_UPSTREAM': f'https://127.0.0.1:{port}',
            'URL_GUARD_BIND': '127.0.0.1',
            'URL_GUARD_PORT': str(gate_port),
            'URL_GUARD_STRICT': '1',
            'URL_GUARD_TLS_VERIFY': '1',
            'URL_GUARD_CA_FILE': cert,
            'URL_GUARD_TLS_NAME': 'manager.example.com',
        })
        gate = GuardServer(('127.0.0.1', gate_port), Config())
        threading.Thread(target=gate.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True).start()
        self.addCleanup(gate.shutdown)
        self.addCleanup(gate.server_close)
        time.sleep(0.1)
        built = build_guarded(SECRET, 'GET', '/api/portal/products/', '', b'')
        conn = http.client.HTTPConnection('127.0.0.1', gate_port, timeout=5)
        conn.request('GET', built['url'], headers={
            'X-Forwarded-Host': DOMAIN,
            'X-Real-IP': '203.0.113.10',
            'Host': DOMAIN,
        })
        resp = conn.getresponse()
        resp.read()
        conn.close()
        self.assertEqual(resp.status, 200)
        self.assertEqual(upstream.seen[0], f'manager.example.com:{port}')


class NginxRenderTests(unittest.TestCase):
    def test_full_config_locks_domain_and_plain_api(self):
        flags = {'ipv6': False, 'stapling': True, 'hsts': True, 'domainonly': True}
        repl = self._repl('')
        site = render_text('ispweb.conf.template', repl, flags)
        headers = render_text('ispweb-headers.conf', repl, flags)
        self.assertIn('server_name portal.example.com;', site)
        self.assertIn('return 444;', site)
        self.assertIn('return 301 https://portal.example.com$request_uri;', site)
        self.assertIn('listen 443 ssl http2;', site)
        self.assertIn('location ^~ /api/ { return 444; }', site)
        self.assertIn('location ^~ /ws/ { return 444; }', site)
        self.assertIn('proxy_pass http://127.0.0.1:8765;', site)
        self.assertIn('http://127.0.0.1:8000', site)
        self.assertNotIn('listen [::]:', site)
        self.assertIn('ssl_stapling on;', site)
        self.assertIn('Strict-Transport-Security', headers)
        plain = render_text('ispweb-headers.conf', repl, {'ipv6': False, 'stapling': False, 'hsts': False})
        self.assertNotIn('Strict-Transport-Security', plain)
        self.assertIn('if ($ispweb_ip_host = 1) { return 444; }', site)
        self.assertNotIn('listen 443 ssl http2 default_server;', site)

    @staticmethod
    def _repl(public_ip):
        from types import SimpleNamespace
        return build_replacements(SimpleNamespace(
            domain=DOMAIN, api='http://127.0.0.1:8000', web_root='/opt/ispweb/current/dist',
            guard_port='8765', ssl_cert='/etc/ispweb/ssl/fullchain.pem',
            ssl_key='/etc/ispweb/ssl/privkey.pem', ssl_trusted='/etc/ispweb/ssl/chain.pem',
            public_ip=public_ip,
        ))

    def test_ip_access_makes_portal_default_server(self):
        flags = {'ipv6': True, 'stapling': False, 'hsts': True, 'ipaccess': True}
        site = render_text('ispweb.conf.template', self._repl('8.8.8.8'), flags)
        self.assertIn('server_name portal.example.com 8.8.8.8;', site)
        self.assertIn('listen 443 ssl http2 default_server;', site)
        self.assertIn('listen [::]:443 ssl http2 default_server;', site)
        self.assertIn('return 301 https://8.8.8.8$request_uri;', site)
        self.assertIn(r'if ($host !~ "^(portal\.example\.com|8\.8\.8\.8)$") { return 444; }', site)
        self.assertNotIn('$ispweb_ip_host', site)
        self.assertEqual(site.count('default_server;'), 4)


class EdgeCheckTests(unittest.TestCase):
    def _headers(self, host):
        return {'x-forwarded-host': host, 'origin': f'https://{host}', 'referer': f'https://{host}/console'}

    def test_domain_only_rejects_ip(self):
        check_edge(self._headers(DOMAIN), (DOMAIN,))
        with self.assertRaises(GuardError):
            check_edge(self._headers('8.8.8.8'), (DOMAIN,))
        with self.assertRaises(GuardError):
            check_edge(self._headers('portal'), DOMAIN)

    def test_ip_host_needs_matching_origin(self):
        hosts = (DOMAIN, '8.8.8.8')
        check_edge(self._headers('8.8.8.8'), hosts)
        mixed = self._headers('8.8.8.8')
        mixed['origin'] = f'https://{DOMAIN}'
        with self.assertRaises(GuardError):
            check_edge(mixed, hosts)


if __name__ == '__main__':
    unittest.main()
