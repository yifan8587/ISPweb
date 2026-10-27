#!/usr/bin/env bash
# 被 deploy 目录下的脚本 source。

log() { printf '[ispweb] %s\n' "$*"; }
die() { printf '[ispweb] 错误: %s\n' "$*" >&2; exit 1; }

require_root() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || die "请使用 root 执行（sudo）"
}

require_supported_ubuntu() {
  [[ -f /etc/os-release ]] || die "无法识别操作系统"
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" || ( "${VERSION_ID:-}" != "22.04" && "${VERSION_ID:-}" != "24.04" ) ]]; then
    if [[ "${FORCE_OS:-0}" == "1" ]]; then
      log "当前系统为 ${ID:-unknown} ${VERSION_ID:-unknown}，已指定 --force-os，继续执行"
      return
    fi
    die "安装脚本面向 Ubuntu 22.04 / 24.04，当前为 ${ID:-unknown} ${VERSION_ID:-unknown}。实验环境可加 --force-os"
  fi
}

# 本机出口公网 IPv4。先看网卡上的公网地址，NAT 后再问外部服务。
detect_public_ip() {
  local ip
  for ip in $(hostname -I 2>/dev/null); do
    if python3 "$SCRIPT_DIR/lib/project_config.py" validate-ip "$ip" >/dev/null 2>&1; then
      printf '%s' "$ip"
      return 0
    fi
  done
  for url in https://api.ipify.org https://ifconfig.me/ip https://ipv4.icanhazip.com; do
    ip=$(curl -4 -fsS --max-time 5 "$url" 2>/dev/null | tr -d '[:space:]' || true)
    if [[ -n "$ip" ]] && python3 "$SCRIPT_DIR/lib/project_config.py" validate-ip "$ip" >/dev/null 2>&1; then
      printf '%s' "$ip"
      return 0
    fi
  done
  return 1
}

ipv6_enabled() {
  [[ -r /proc/net/if_inet6 ]] && grep -q '[^[:space:]]' /proc/net/if_inet6
}

load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || die "找不到环境文件: $file"
  # shellcheck disable=SC1090
  set -a
  source "$file"
  set +a
}

env_get() {
  python3 - "$1" "$2" <<'PY'
import sys
from pathlib import Path
file_path, key = sys.argv[1], sys.argv[2]
for line in Path(file_path).read_text(encoding='utf-8').splitlines():
    if line.startswith(key + '='):
        print(line.split('=', 1)[1], end='')
        break
PY
}

secret_fingerprint() {
  printf '%s' "$1" | sha256sum | awk '{print substr($1, 1, 12)}'
}
