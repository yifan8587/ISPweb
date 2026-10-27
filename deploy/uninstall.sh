#!/usr/bin/env bash
# 停止 ISPweb 站点和服务。默认保留 /etc/ispweb 中的证书与环境文件。
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"

PURGE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge) PURGE=1; shift ;;
    -h|--help)
      echo "用法: sudo ./deploy/uninstall.sh [--purge]"
      exit 0
      ;;
    *) die "未知参数: $1" ;;
  esac
done

require_root
systemctl disable --now ispweb-urlguard.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/ispweb-urlguard.service
systemctl daemon-reload || true
rm -f /etc/nginx/sites-enabled/ispweb.conf
rm -f /etc/nginx/sites-available/ispweb.conf
rm -f /etc/nginx/conf.d/ispweb-security.conf
rm -f /etc/nginx/snippets/ispweb-headers.conf
rm -f /etc/fail2ban/jail.d/ispweb.conf /etc/fail2ban/filter.d/ispweb-nginx.conf
if command -v nginx >/dev/null && [[ -d /etc/nginx ]]; then
  nginx -t && systemctl reload nginx || true
fi
if command -v fail2ban-client >/dev/null; then
  systemctl reload fail2ban >/dev/null 2>&1 || true
fi
rm -rf /opt/ispweb
if [[ "$PURGE" == "1" ]]; then
  rm -rf /etc/ispweb
  userdel ispweb >/dev/null 2>&1 || true
  groupdel ispweb >/dev/null 2>&1 || true
  log "已删除程序、配置、自签证书和系统用户。Let's Encrypt 证书仍留在 /etc/letsencrypt"
else
  log "已停止站点并删除 /opt/ispweb。/etc/ispweb 中的环境文件和自签证书仍保留"
fi
