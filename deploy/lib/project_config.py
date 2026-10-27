#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验域名、API 地址，并把 API 地址写回 vite.config.js。"""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path


DOMAIN_RE = re.compile(
    r'^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$'
)
VITE_RE = re.compile(
    r"(// DEPLOY_API_PROXY_TARGET_BEGIN\n"
    r"const API_PROXY_TARGET = process\.env\.VITE_API_PROXY_TARGET \|\| ')"
    r"([^']*)"
    r"(')"
)


def normalize_domain(value: str) -> str:
    domain = (value or '').strip().lower().rstrip('.')
    if not DOMAIN_RE.fullmatch(domain):
        raise SystemExit('域名格式不正确。请填写完整域名，IP 地址不能作为访问入口')
    return domain


def normalize_public_ip(value: str) -> str:
    """门户服务器的公网 IPv4。内网和保留地址不能作为公网入口。"""
    import ipaddress
    raw = (value or '').strip()
    try:
        address = ipaddress.IPv4Address(raw)
    except ValueError:
        raise SystemExit(f'公网 IP 格式不正确: {raw or "空"}')
    if not address.is_global:
        raise SystemExit(f'{address} 不是公网地址。NAT 后的服务器请用 --public-ip 填写出口公网 IP')
    return str(address)


def normalize_api(value: str) -> str:
    raw = (value or '').strip()
    if any(ch in raw for ch in '\'" \t\r\n'):
        raise SystemExit('API 地址包含空格或引号')
    parts = urllib.parse.urlsplit(raw)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise SystemExit('API 地址需要以 http:// 或 https:// 开头，并包含主机')
    if parts.username or parts.password or parts.fragment or parts.query:
        raise SystemExit('API 地址只保留协议、主机和端口')
    if parts.path not in ('', '/'):
        raise SystemExit('API 地址不要带路径。门户接口路径固定为 /api')
    return f'{parts.scheme}://{parts.netloc}'


def api_is_loopback(value: str) -> bool:
    parts = urllib.parse.urlsplit(normalize_api(value))
    return parts.hostname in ('127.0.0.1', 'localhost', '::1')


def set_vite_api(vite_path: str, api: str) -> str:
    path = Path(vite_path)
    text = path.read_text(encoding='utf-8')
    match = VITE_RE.search(text)
    if not match:
        raise SystemExit('vite.config.js 缺少 DEPLOY_API_PROXY_TARGET 标记，无法写入 API 地址')
    api = normalize_api(api)
    if match.group(2) == api:
        return 'unchanged'
    updated = VITE_RE.sub(lambda item: item.group(1) + api + item.group(3), text, count=1)
    path.write_text(updated, encoding='utf-8')
    return 'updated'


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('用法: project_config.py validate-domain|validate-ip|validate-api|set-vite ...')
    cmd = sys.argv[1]
    if cmd == 'validate-domain':
        print(normalize_domain(sys.argv[2]))
    elif cmd == 'validate-ip':
        print(normalize_public_ip(sys.argv[2]))
    elif cmd == 'validate-api':
        print(normalize_api(sys.argv[2]))
    elif cmd == 'api-is-loopback':
        print('yes' if api_is_loopback(sys.argv[2]) else 'no')
    elif cmd == 'set-vite':
        print(set_vite_api(sys.argv[2], sys.argv[3]))
    else:
        raise SystemExit(f'未知命令: {cmd}')


if __name__ == '__main__':
    main()
