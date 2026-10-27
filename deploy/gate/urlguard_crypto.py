#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL 编码混淆与参数杂凑。

浏览器端 src/utils/urlguard.js 必须使用同一套载荷、异或、Base64URL 与 HMAC。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
import urllib.parse


class GuardError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def obfuscate_encode(text: str, secret: str) -> str:
    key = hashlib.sha256(secret.encode('utf-8')).digest()
    raw = text.encode('utf-8')
    mixed = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
    return base64.urlsafe_b64encode(mixed).decode('ascii').rstrip('=')


def obfuscate_decode(token: str, secret: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,16384}', token or ''):
        raise GuardError('bad_token')
    pad = '=' * (-len(token) % 4)
    try:
        mixed = base64.urlsafe_b64decode(token + pad)
    except Exception as exc:
        raise GuardError('bad_token') from exc
    key = hashlib.sha256(secret.encode('utf-8')).digest()
    raw = bytes(mixed[i] ^ key[i % len(key)] for i in range(len(mixed)))
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise GuardError('bad_token') from exc


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign_message(secret: str, method: str, token: str, body_hash: str, timestamp: str, nonce: str) -> str:
    message = f'{method}\n{token}\n{body_hash}\n{timestamp}\n{nonce}'
    return hmac.new(secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()


def dumps_payload(method: str, path: str, query: str) -> str:
    return json.dumps(
        {'v': 1, 'm': method, 'p': path, 'q': query},
        ensure_ascii=False,
        separators=(',', ':'),
    )


def build_guarded(secret, method, path, query, body, channel='http', timestamp=None, nonce=None):
    verb = method.upper()
    token = obfuscate_encode(dumps_payload(verb, path, query), secret)
    ts = str(int(time.time()) if timestamp is None else timestamp)
    nonce = nonce or secrets.token_hex(16)
    body_hash = sha256_hex(body)
    mac = sign_message(secret, verb, token, body_hash, ts, nonce)
    prefix = '/_gws/' if channel == 'ws' else '/_g/'
    return {
        'url': f'{prefix}{token}?_t={ts}&_n={nonce}&_h={mac}',
        'token': token,
        'timestamp': ts,
        'nonce': nonce,
        'body_hash': body_hash,
    }


class NonceCache:
    def __init__(self, max_items: int = 100000):
        self._lock = threading.Lock()
        self._items: dict[str, int] = {}
        self._max = max_items

    def commit(self, nonce: str, now: int, ttl: int) -> None:
        with self._lock:
            expiry = self._items.get(nonce)
            if expiry is not None and expiry > now:
                raise GuardError('replay')
            self._items[nonce] = now + ttl
            if len(self._items) <= self._max:
                return
            self._items = {key: exp for key, exp in self._items.items() if exp > now}
            if len(self._items) > self._max:
                overflow = len(self._items) - self._max
                for key in list(self._items)[:overflow]:
                    del self._items[key]


def _split_channel(path: str) -> tuple[str, str]:
    if path.startswith('/_gws/'):
        token = path[len('/_gws/'):]
        channel = 'ws'
    elif path.startswith('/_g/'):
        token = path[len('/_g/'):]
        channel = 'http'
    else:
        raise GuardError('bad_channel')
    if not token or '/' in token:
        raise GuardError('bad_token')
    return channel, token


def _parse_outer(query: str) -> tuple[str, str, str]:
    if any(ch in query for ch in '\r\n\x00'):
        raise GuardError('bad_outer')
    try:
        pairs = urllib.parse.parse_qsl(query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise GuardError('bad_outer') from exc
    found: dict[str, str] = {}
    for key, value in pairs:
        if key in found:
            raise GuardError('dup_param')
        found[key] = value
    if set(found) != {'_t', '_n', '_h'}:
        raise GuardError('bad_outer')
    ts, nonce, mac = found['_t'], found['_n'], found['_h']
    if not re.fullmatch(r'[0-9]{10}', ts):
        raise GuardError('bad_time')
    if not re.fullmatch(r'[0-9a-f]{32}', nonce):
        raise GuardError('bad_nonce')
    if not re.fullmatch(r'[0-9a-f]{64}', mac):
        raise GuardError('bad_hash')
    return ts, nonce, mac


PORTAL_HTTP_EXACT = {
    '/api/auth/token',
    '/api/auth/token/',
    '/api/auth/token/refresh',
    '/api/auth/token/refresh/',
}
PORTAL_HTTP_PREFIXES = (
    '/api/auth/me',
    '/api/portal/',
    '/api/customer/payment-transactions/',
)


def validate_inner_path(path: str, channel: str) -> None:
    if channel == 'ws':
        if not path.startswith('/ws/resource/vnc/'):
            raise GuardError('bad_path')
    elif path not in PORTAL_HTTP_EXACT and path not in {'/api/portal', '/api/customer/payment-transactions'}:
        if not any(path.startswith(prefix) for prefix in PORTAL_HTTP_PREFIXES):
            raise GuardError('bad_path')
    if len(path) > 512 or any(ch in path for ch in '\\#?\x00') or '//' in path or '%' in path:
        raise GuardError('bad_path')
    for part in path.split('/')[1:]:
        if part in ('.', '..'):
            raise GuardError('bad_path')


def validate_inner_query(query: str) -> None:
    if len(query) > 8192 or any(ch in query for ch in '\r\n\x00#?') or '?' in query:
        raise GuardError('bad_query')
    index = 0
    while index < len(query):
        if query[index] == '%':
            piece = query[index + 1:index + 3]
            if not re.fullmatch(r'[0-9A-Fa-f]{2}', piece):
                raise GuardError('bad_query')
            index += 3
            continue
        index += 1
    if not query:
        return
    try:
        pairs = urllib.parse.parse_qsl(query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise GuardError('bad_query') from exc
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise GuardError('dup_param')


def open_request(method, target_path, outer_query, body, secret, skew, nonces, channel_expected=None):
    verb = (method or '').upper()
    if verb not in {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'}:
        raise GuardError('bad_method')
    channel, token = _split_channel(target_path)
    if channel_expected and channel != channel_expected:
        raise GuardError('bad_channel')
    ts, nonce, mac = _parse_outer(outer_query or '')
    now = int(time.time())
    if abs(now - int(ts)) > int(skew):
        raise GuardError('expired')
    body_hash = sha256_hex(body or b'')
    expect = sign_message(secret, verb, token, body_hash, ts, nonce)
    if not hmac.compare_digest(expect, mac):
        raise GuardError('bad_hash')
    nonces.commit(nonce, now, int(skew))
    try:
        payload = json.loads(obfuscate_decode(token, secret))
    except json.JSONDecodeError as exc:
        raise GuardError('bad_token') from exc
    if not isinstance(payload, dict) or payload.get('v') != 1 or payload.get('m') != verb:
        raise GuardError('bad_token')
    path = payload.get('p')
    query = payload.get('q')
    if not isinstance(path, str) or not isinstance(query, str):
        raise GuardError('bad_token')
    validate_inner_path(path, channel)
    validate_inner_query(query)
    return {'channel': channel, 'path': path, 'query': query, 'method': verb}
