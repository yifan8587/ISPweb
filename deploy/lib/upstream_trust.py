#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装时核对管理端 HTTPS。公共 CA 不信任时，钉住当前证书。"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import re
import socket
import ssl
import subprocess
import tempfile
import urllib.parse
from pathlib import Path


def _split(api: str):
    parts = urllib.parse.urlsplit(api)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise SystemExit('API 地址无法解析')
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    return parts, port


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def fetch_peer_pem(host: str, port: int, timeout: float = 8) -> bytes:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                der = tls.getpeercert(binary_form=True)
    except TimeoutError as exc:
        raise SystemExit(f'连接管理端 {host}:{port} 超时。请确认该端口已对门户服务器放行') from exc
    except ConnectionRefusedError as exc:
        raise SystemExit(f'管理端 {host}:{port} 拒绝连接。请确认门户 API 已监听，并且防火墙放行') from exc
    except ssl.SSLError as exc:
        raise SystemExit(
            f'管理端 {host}:{port} 没有完成 TLS 握手（{exc}）。'
            '请在 ISPmanager 上执行 setup-ssl.sh，让门户 API 使用 HTTPS'
        ) from exc
    except OSError as exc:
        raise SystemExit(f'无法连接管理端 {host}:{port}：{exc}') from exc
    if not der:
        raise SystemExit('管理端没有返回证书')
    return ssl.DER_cert_to_PEM_cert(der).encode('ascii')


def cert_names(pem: bytes) -> tuple[list[str], list[str]]:
    with tempfile.NamedTemporaryFile() as handle:
        handle.write(pem)
        handle.flush()
        proc = subprocess.run(
            ['openssl', 'x509', '-in', handle.name, '-noout', '-text'],
            capture_output=True,
            check=False,
        )
    text = proc.stdout.decode('utf-8', 'replace')
    dns = re.findall(r'DNS:([^,\s]+)', text)
    ips = re.findall(r'IP Address:([^,\s]+)', text)
    if not dns:
        subject = re.search(r'Subject:.*?\bCN\s*=\s*([^,\n/]+)', text)
        if subject:
            dns = [subject.group(1).strip()]
    return dns, ips


def choose_tls_name(host: str, dns_names: list[str]) -> str:
    if not _is_ip(host):
        return ''
    for name in dns_names:
        lowered = name.strip().lower().rstrip('.')
        if lowered and lowered != 'localhost':
            return lowered
    return ''


def fingerprint(pem: bytes) -> str:
    der = ssl.PEM_cert_to_DER_cert(pem.decode('ascii'))
    return hashlib.sha256(der).hexdigest()


def trusted(host: str, port: int, server_name: str, ca_file: str = '', timeout: float = 8) -> tuple[bool, str]:
    context = ssl.create_default_context()
    if ca_file:
        context.load_verify_locations(ca_file)
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=server_name) as tls:
                tls.do_handshake()
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'
    return True, ''


def prepare(api: str, ca_file: str, pin_path: str, verify: bool) -> None:
    parts, port = _split(api)
    if parts.scheme != 'https' or parts.hostname in ('127.0.0.1', 'localhost', '::1'):
        print('MODE=plain')
        print('CA_FILE=')
        print('TLS_NAME=')
        print('FINGERPRINT=')
        return

    pem = fetch_peer_pem(parts.hostname, port)
    dns_names, _ips = cert_names(pem)
    tls_name = choose_tls_name(parts.hostname, dns_names)
    server_name = tls_name or parts.hostname
    digest = fingerprint(pem)
    mode = 'system'
    used_ca = ''

    if not verify:
        mode = 'insecure'
        used_ca = ca_file
    elif ca_file:
        ok, err = trusted(parts.hostname, port, server_name, ca_file)
        if not ok:
            raise SystemExit(f'使用指定 CA 校验管理端证书失败：{err}')
        mode = 'provided'
        used_ca = ca_file
    else:
        ok, _err = trusted(parts.hostname, port, server_name)
        if ok:
            mode = 'system'
        else:
            path = Path(pin_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pem)
            path.chmod(0o644)
            ok, err = trusted(parts.hostname, port, server_name, str(path))
            if not ok:
                raise SystemExit(f'钉住管理端证书后仍然无法校验：{err}')
            mode = 'pinned'
            used_ca = str(path)

    print(f'MODE={mode}')
    print(f'CA_FILE={used_ca}')
    print(f'TLS_NAME={tls_name}')
    print(f'FINGERPRINT={digest}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', required=True)
    parser.add_argument('--ca-file', default='')
    parser.add_argument('--pin-path', default='/etc/ispweb/ssl/upstream.pem')
    parser.add_argument('--verify', default='1')
    args = parser.parse_args()
    prepare(args.api, args.ca_file, args.pin_path, args.verify.strip() != '0')


if __name__ == '__main__':
    main()
