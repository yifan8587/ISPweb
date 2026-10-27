#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Nginx 模板渲染成可安装的站点配置。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


NGINX_DIR = Path(__file__).resolve().parents[1] / 'nginx'
TOKEN_RE = re.compile(r'__[A-Z0-9_]+__')
# 行首标记，例如 `#__IPV6__ `。一行可以带多个，全部开启才保留这一行。
MARK_RE = re.compile(r'#__([A-Z0-9]+)__ ')


def render_text(name: str, replacements: dict[str, str], flags: dict[str, bool]) -> str:
    text = (NGINX_DIR / name).read_text(encoding='utf-8')
    for key, value in replacements.items():
        if '\n' in value or '\r' in value:
            raise SystemExit(f'{key} 包含换行，拒绝写入 Nginx 配置')
        text = text.replace(key, value)
    kept = []
    for line in text.splitlines(True):
        names = MARK_RE.findall(line)
        if names:
            if not all(flags.get(name.lower()) for name in names):
                continue
            line = MARK_RE.sub('', line)
        kept.append(line)
    rendered = ''.join(kept)
    leftover = TOKEN_RE.findall(rendered)
    if leftover:
        raise SystemExit('模板仍有未替换标记: ' + ', '.join(sorted(set(leftover))))
    return rendered


def build_replacements(args) -> dict[str, str]:
    return {
        '__DOMAIN__': args.domain,
        '__API_UPSTREAM__': args.api,
        '__WEB_ROOT__': args.web_root,
        '__GUARD_PORT__': str(args.guard_port),
        '__SSL_CERT__': args.ssl_cert,
        '__SSL_KEY__': args.ssl_key,
        '__SSL_TRUSTED__': args.ssl_trusted or args.ssl_cert,
        '__PUBLIC_IP__': args.public_ip,
        '__SERVER_NAMES__': f'{args.domain} {args.public_ip}'.strip(),
        '__HOST_RE__': '^(' + '|'.join(re.escape(h) for h in (args.domain, args.public_ip) if h) + ')$',
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('full', 'bootstrap'), required=True)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--api', required=True)
    parser.add_argument('--web-root', required=True)
    parser.add_argument('--guard-port', default='8765')
    parser.add_argument('--ssl-cert', default='')
    parser.add_argument('--ssl-key', default='')
    parser.add_argument('--ssl-trusted', default='')
    parser.add_argument('--ipv6', action='store_true')
    parser.add_argument('--stapling', action='store_true')
    parser.add_argument('--hsts', action='store_true')
    parser.add_argument('--public-ip', default='')
    parser.add_argument('--out', required=True)
    parser.add_argument('--headers-out', default='')
    args = parser.parse_args()
    if args.public_ip and not re.fullmatch(r'(?:\d{1,3}\.){3}\d{1,3}', args.public_ip):
        raise SystemExit('--public-ip 只接受 IPv4 地址')
    flags = {
        'ipv6': args.ipv6, 'stapling': args.stapling, 'hsts': args.hsts,
        'ipaccess': bool(args.public_ip), 'domainonly': not args.public_ip,
    }
    replacements = build_replacements(args)
    template = 'ispweb.conf.template' if args.mode == 'full' else 'ispweb.bootstrap.conf.template'
    Path(args.out).write_text(render_text(template, replacements, flags), encoding='utf-8')
    if args.headers_out:
        Path(args.headers_out).write_text(
            render_text('ispweb-headers.conf', replacements, flags),
            encoding='utf-8',
        )


if __name__ == '__main__':
    main()
