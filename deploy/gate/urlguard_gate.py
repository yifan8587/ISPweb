#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本机访问网关：校验混淆路径和参数杂凑，再转发到 API 上游。只监听 127.0.0.1。"""

from __future__ import annotations

import http.client
import os
import re
import select
import signal
import socket
import socketserver
import ssl
import threading
import time
import urllib.parse

from urlguard_crypto import GuardError, NonceCache, open_request


PASS_REQUEST_HEADERS = {
    'accept',
    'accept-language',
    'authorization',
    'content-type',
    'user-agent',
    'x-user-activity',
}
HOP_RESPONSE_HEADERS = {
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
    'proxy-connection',
    'content-length',
    'server',
}
SENSITIVE_PREFIXES = ('/api/auth/token', '/api/portal/register')
MAX_HEADER = 65536
MAX_RESPONSE = 32 * 1024 * 1024


class UpstreamError(Exception):
    pass


class PathRate:
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def hit(self, key: str, now: float) -> None:
        with self._lock:
            bucket = [item for item in self._hits.get(key, []) if now - item < self.window]
            if len(bucket) >= self.limit:
                self._hits[key] = bucket
                raise GuardError('rate')
            bucket.append(now)
            self._hits[key] = bucket


class Config:
    def __init__(self):
        self.secret = os.environ.get('URL_GUARD_SECRET', '').strip()
        self.domain = os.environ.get('DOMAIN', '').strip().lower()
        self.public_ip = os.environ.get('PUBLIC_IP', '').strip()
        self.api_upstream = os.environ.get('API_UPSTREAM', '').strip()
        self.bind = os.environ.get('URL_GUARD_BIND', '127.0.0.1').strip() or '127.0.0.1'
        self.port = int(os.environ.get('URL_GUARD_PORT', '8765'))
        self.skew = int(os.environ.get('URL_GUARD_SKEW', '120'))
        self.strict = os.environ.get('URL_GUARD_STRICT', '1').strip() != '0'
        self.max_body = int(os.environ.get('URL_GUARD_MAX_BODY', '2097152'))
        self.portal_api_secret = os.environ.get('PORTAL_API_SECRET', '').strip()
        self.tls_verify = os.environ.get('URL_GUARD_TLS_VERIFY', '1').strip() != '0'
        self.ca_file = os.environ.get('URL_GUARD_CA_FILE', '').strip()
        self.tls_name = os.environ.get('URL_GUARD_TLS_NAME', '').strip().lower()
        self.nonces = NonceCache()
        self.login_rate = PathRate(20, 60)
        if not self.secret or not self.domain or not self.api_upstream:
            raise SystemExit('缺少 URL_GUARD_SECRET、DOMAIN 或 API_UPSTREAM')
        if self.bind not in ('127.0.0.1', '::1'):
            raise SystemExit('URL_GUARD_BIND 只能是 127.0.0.1')
        if self.public_ip and not _valid_ipv4(self.public_ip):
            raise SystemExit('PUBLIC_IP 不是合法的 IPv4 地址')
        self.hosts = (self.domain, self.public_ip) if self.public_ip else (self.domain,)
        if self.tls_name and not _valid_server_name(self.tls_name):
            raise SystemExit('URL_GUARD_TLS_NAME 不是合法主机名')
        if self.ca_file and not os.access(self.ca_file, os.R_OK):
            raise SystemExit(f'无法读取 URL_GUARD_CA_FILE: {self.ca_file}')
        if self.portal_api_secret and len(self.portal_api_secret) < 32:
            raise SystemExit('PORTAL_API_SECRET 至少 32 位')
        if any(ch in self.portal_api_secret for ch in '\r\n\x00'):
            raise SystemExit('PORTAL_API_SECRET 不能包含换行')
        if not _loopback_upstream(self.api_upstream) and not self.portal_api_secret:
            raise SystemExit('远程 API 必须配置 PORTAL_API_SECRET，并与 ISPmanager 使用同一密钥')


def log(level: str, **fields) -> None:
    text = ' '.join(f'{key}={value}' for key, value in fields.items())
    print(f'{level} {text}', flush=True)


def read_until(sock, marker: bytes, limit: int, initial: bytes = b'') -> tuple[bytes, bytes]:
    data = initial
    while marker not in data:
        if len(data) > limit:
            raise GuardError('header_too_large')
        chunk = sock.recv(4096)
        if not chunk:
            raise GuardError('client_closed')
        data += chunk
    index = data.index(marker)
    return data[:index], data[index + len(marker):]


def parse_request(head: bytes):
    try:
        text = head.decode('iso-8859-1')
    except UnicodeDecodeError as exc:
        raise GuardError('bad_request') from exc
    lines = text.split('\r\n')
    parts = lines[0].split(' ')
    if len(parts) != 3:
        raise GuardError('bad_request')
    method, target, version = parts
    if version not in ('HTTP/1.0', 'HTTP/1.1') or not target.startswith('/'):
        raise GuardError('bad_request')
    path, _, query = target.partition('?')
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line:
            continue
        if ':' not in line:
            raise GuardError('bad_header')
        name, value = line.split(':', 1)
        name = name.strip().lower()
        value = value.strip()
        if not name or name in headers or '\x00' in value or '\r' in value or '\n' in value:
            raise GuardError('bad_header')
        if len(value) > 16384:
            raise GuardError('bad_header')
        headers[name] = value
    return method, path, query, headers


def peer_host(addr) -> str:
    host = addr[0]
    if host.startswith('::ffff:'):
        return host.split('::ffff:', 1)[1]
    return host


def assert_local(addr) -> None:
    if peer_host(addr) not in ('127.0.0.1', '::1'):
        raise GuardError('bad_peer')


def client_ip(headers, addr) -> str:
    ip = headers.get('x-real-ip', '') or peer_host(addr)
    if not re.fullmatch(r'[0-9a-fA-F:.]+', ip or ''):
        return peer_host(addr)
    return ip


def check_edge(headers, hosts) -> None:
    if isinstance(hosts, str):
        hosts = (hosts,)
    forwarded = headers.get('x-forwarded-host', '').split(',')[0].strip().lower()
    if forwarded.startswith('['):
        raise GuardError('bad_host')
    forwarded = forwarded.split(':', 1)[0]
    if forwarded not in hosts:
        raise GuardError('bad_host')
    allowed = f'https://{forwarded}'
    origin = headers.get('origin', '')
    if origin and origin != allowed:
        raise GuardError('bad_origin')
    referer = headers.get('referer', '')
    if referer and referer != allowed and not referer.startswith(allowed + '/'):
        raise GuardError('bad_referer')


def read_body(sock, headers, rest: bytes, max_body: int) -> bytes:
    if 'transfer-encoding' in headers:
        raise GuardError('bad_body')
    if 'content-length' not in headers:
        if rest:
            raise GuardError('bad_body')
        return b''
    try:
        length = int(headers['content-length'])
    except ValueError as exc:
        raise GuardError('bad_body') from exc
    if length < 0 or length > max_body:
        raise GuardError('bad_body')
    while len(rest) < length:
        chunk = sock.recv(min(65536, length - len(rest)))
        if not chunk:
            raise GuardError('bad_body')
        rest += chunk
    if rest[length:]:
        raise GuardError('bad_body')
    return rest[:length]


def send_simple(sock, status: int, reason: str, body: bytes, content_type: str = 'text/plain; charset=utf-8') -> None:
    head = (
        f'HTTP/1.1 {status} {reason}\r\n'
        f'Content-Type: {content_type}\r\n'
        f'Content-Length: {len(body)}\r\n'
        'Connection: close\r\n'
        'Cache-Control: no-store\r\n'
        '\r\n'
    )
    sock.sendall(head.encode('ascii') + body)


def _loopback_upstream(api_upstream: str) -> bool:
    host = urllib.parse.urlsplit(api_upstream).hostname or ''
    return host in ('127.0.0.1', 'localhost', '::1')


def upstream_ssl_context(cfg: Config):
    context = ssl.create_default_context()
    if cfg.ca_file:
        context.load_verify_locations(cfg.ca_file)
    if not cfg.tls_verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _valid_ipv4(value: str) -> bool:
    if not re.fullmatch(r'(?:\d{1,3}\.){3}\d{1,3}', value):
        return False
    return all(0 <= int(part) <= 255 for part in value.split('.'))


def _valid_server_name(value: str) -> bool:
    if value == 'localhost':
        return True
    if re.fullmatch(r'(?:\d{1,3}\.){3}\d{1,3}', value):
        return all(0 <= int(part) <= 255 for part in value.split('.'))
    return bool(re.fullmatch(
        r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',
        value,
    ))


def upstream_server_name(cfg: Config, parts) -> str:
    return cfg.tls_name or parts.hostname


def host_header(name: str, port: int, default_port: int) -> str:
    if port == default_port:
        return name
    return f'{name}:{port}'


class UpstreamHTTPSConnection(http.client.HTTPSConnection):
    """连到 URL 里的地址，SNI 和 Host 使用证书上的域名。"""

    def __init__(self, host, port, context, timeout, server_name):
        super().__init__(host, port, timeout=timeout, context=context)
        self.server_name = server_name

    def connect(self):
        http.client.HTTPConnection.connect(self)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.server_name)

    def putrequest(self, method, url, skip_host=False, skip_accept_encoding=False):
        super().putrequest(method, url, skip_host=True, skip_accept_encoding=skip_accept_encoding)
        self.putheader('Host', host_header(self.server_name, self.port, 443))


def open_upstream(cfg: Config):
    parts, port = upstream_parts(cfg.api_upstream)
    if parts.scheme == 'https':
        return UpstreamHTTPSConnection(
            parts.hostname,
            port,
            context=upstream_ssl_context(cfg),
            timeout=3600,
            server_name=upstream_server_name(cfg, parts),
        ), parts
    return http.client.HTTPConnection(parts.hostname, port, timeout=3600), parts


def portal_headers(cfg: Config, client: str) -> dict[str, str]:
    headers = {
        'X-Forwarded-Proto': 'https',
        'X-Real-IP': client,
        'X-Forwarded-For': client,
        'X-Portal-Origin': f'https://{cfg.domain}',
    }
    if cfg.portal_api_secret:
        headers['X-ISP-Portal-Key'] = cfg.portal_api_secret
    return headers


def upstream_parts(api_upstream: str):
    parts = urllib.parse.urlsplit(api_upstream)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise UpstreamError('bad upstream')
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    return parts, port


def forward_http(sock, cfg: Config, opened, headers, body: bytes, client: str) -> None:
    parts, port = upstream_parts(cfg.api_upstream)
    path = opened['path']
    if parts.path not in ('', '/'):
        path = parts.path.rstrip('/') + path
    if opened['query']:
        path += '?' + opened['query']
    if any(opened['path'].startswith(prefix) for prefix in SENSITIVE_PREFIXES):
        cfg.login_rate.hit(client, time.time())
    request_headers = portal_headers(cfg, client)
    for name in PASS_REQUEST_HEADERS:
        if name in headers:
            request_headers[name] = headers[name]
    try:
        conn, _parts = open_upstream(cfg)
        conn.request(opened['method'], path, body=body or None, headers=request_headers)
        resp = conn.getresponse()
        payload = resp.read(MAX_RESPONSE + 1)
    except GuardError:
        raise
    except Exception as exc:
        raise UpstreamError(str(exc)) from exc
    if len(payload) > MAX_RESPONSE:
        conn.close()
        raise UpstreamError('response too large')
    lines = [f'HTTP/1.1 {resp.status} {resp.reason or "OK"}']
    for key, value in resp.getheaders():
        if key.lower() in HOP_RESPONSE_HEADERS:
            continue
        try:
            value.encode('latin-1')
        except UnicodeEncodeError:
            continue
        lines.append(f'{key}: {value}')
    lines.append(f'Content-Length: {len(payload)}')
    lines.append('Connection: close')
    raw = ('\r\n'.join(lines) + '\r\n\r\n').encode('latin-1', 'replace') + payload
    sock.sendall(raw)
    conn.close()
    log('INFO', event='proxy', ip=client, method=opened['method'], path=opened['path'], status=resp.status)


def splice(left, right) -> None:
    left.settimeout(None)
    right.settimeout(None)
    pair = [left, right]
    try:
        while True:
            readable, _, _ = select.select(pair, [], [], 3600)
            if not readable:
                return
            for current in readable:
                other = right if current is left else left
                data = current.recv(65536)
                if not data:
                    return
                other.sendall(data)
                # TLS 已解密的剩余数据留在 SSL 缓冲里，select 看不到，必须当场取完。
                pending = getattr(current, 'pending', None)
                while pending is not None and pending() > 0:
                    data = current.recv(65536)
                    if not data:
                        return
                    other.sendall(data)
    finally:
        for current in pair:
            try:
                current.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                current.close()
            except OSError:
                pass


def handle_ws(sock, rest: bytes, headers, opened, cfg: Config, client: str) -> None:
    key = headers.get('sec-websocket-key', '')
    if not key or headers.get('upgrade', '').lower() != 'websocket':
        raise GuardError('bad_ws')
    parts, port = upstream_parts(cfg.api_upstream)
    path = opened['path']
    if parts.path not in ('', '/'):
        path = parts.path.rstrip('/') + path
    if opened['query']:
        path += '?' + opened['query']
    name = upstream_server_name(cfg, parts)
    host = host_header(name, port, 443 if parts.scheme == 'https' else 80)
    lines = [
        f'GET {path} HTTP/1.1',
        f'Host: {host}',
        'Upgrade: websocket',
        'Connection: Upgrade',
        f'Sec-WebSocket-Key: {key}',
        f'Sec-WebSocket-Version: {headers.get("sec-websocket-version", "13")}',
    ]
    protocol = headers.get('sec-websocket-protocol', '')
    if protocol:
        lines.append(f'Sec-WebSocket-Protocol: {protocol}')
    # 已在 check_edge 核对过，管理端只认门户域名。
    if headers.get('origin', ''):
        lines.append(f'Origin: https://{cfg.domain}')
    lines.extend([
        'X-Forwarded-Proto: https',
        f'X-Real-IP: {client}',
        f'X-Forwarded-For: {client}',
        f'X-Portal-Origin: https://{cfg.domain}',
    ])
    if cfg.portal_api_secret:
        lines.append(f'X-ISP-Portal-Key: {cfg.portal_api_secret}')
    lines.extend(['', ''])
    try:
        upstream = socket.create_connection((parts.hostname, port), timeout=10)
    except OSError as exc:
        raise UpstreamError(str(exc)) from exc
    upstream.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    try:
        if parts.scheme == 'https':
            upstream = upstream_ssl_context(cfg).wrap_socket(upstream, server_hostname=name)
        upstream.sendall('\r\n'.join(lines).encode('ascii'))
        head, extra = read_until(upstream, b'\r\n\r\n', MAX_HEADER)
        sock.sendall(head + b'\r\n\r\n' + extra)
        status = head.split(b'\r\n', 1)[0]
        log('INFO', event='ws', ip=client, path=opened['path'], status=status.decode('ascii', 'replace'))
        if b' 101 ' not in status:
            return
        if rest:
            upstream.sendall(rest)
        splice(sock, upstream)
        upstream = None
    finally:
        if upstream is not None:
            try:
                upstream.close()
            except OSError:
                pass


def process(sock, addr, cfg: Config) -> None:
    try:
        sock.settimeout(20)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        assert_local(addr)
        head, rest = read_until(sock, b'\r\n\r\n', MAX_HEADER)
        method, path, query, headers = parse_request(head)
        if method == 'GET' and path == '/healthz':
            send_simple(sock, 200, 'OK', b'ok\n')
            return
        check_edge(headers, cfg.hosts)
        client = client_ip(headers, addr)
        if headers.get('upgrade', '').lower() == 'websocket' or path.startswith('/_gws/'):
            opened = open_request(method, path, query, b'', cfg.secret, cfg.skew, cfg.nonces, 'ws')
            if rest:
                raise GuardError('bad_body')
            handle_ws(sock, b'', headers, opened, cfg, client)
            return
        body = read_body(sock, headers, rest, cfg.max_body)
        opened = open_request(method, path, query, body, cfg.secret, cfg.skew, cfg.nonces, 'http')
        forward_http(sock, cfg, opened, headers, body, client)
    except GuardError as exc:
        status = 429 if exc.code == 'rate' else 404
        body = b'' if cfg.strict else f'{{"code":"{exc.code}"}}\n'.encode('ascii')
        try:
            send_simple(sock, status, 'Not Found' if status == 404 else 'Too Many Requests', body)
        except OSError:
            pass
        log('WARN', event='reject', code=exc.code, peer=peer_host(addr))
    except UpstreamError as exc:
        try:
            send_simple(sock, 502, 'Bad Gateway', b'')
        except OSError:
            pass
        log('WARN', event='upstream', detail=f'{type(exc).__name__}: {exc}'[:180])
    except Exception as exc:
        try:
            send_simple(sock, 500, 'Internal Server Error', b'')
        except OSError:
            pass
        log('ERROR', event='crash', detail=type(exc).__name__)
    finally:
        try:
            sock.close()
        except OSError:
            pass


class GuardServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128

    def __init__(self, server_address, config: Config):
        self.config = config
        super().__init__(server_address, ConnectionHandler)


class ConnectionHandler(socketserver.BaseRequestHandler):
    def handle(self):
        process(self.request, self.client_address, self.server.config)


def main() -> None:
    cfg = Config()
    if cfg.bind == '::1':
        GuardServer.address_family = socket.AF_INET6
    server = GuardServer((cfg.bind, cfg.port), cfg)

    def stop(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log('INFO', event='listen', addr=f'{cfg.bind}:{cfg.port}', domain=cfg.domain, strict=int(cfg.strict))
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
