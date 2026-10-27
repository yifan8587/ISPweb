#!/usr/bin/env bash
# 用新的安装包替换正在运行的 ISPweb，并在失败时回滚。
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/release.sh"

usage() {
  cat <<'EOF'
用法: sudo ./deploy/update.sh /path/ispweb-1.0.2-时间戳.tar.gz [--api https://manager.example.com:8443] [--portal-secret 密钥]
                               [--public-ip 公网IP | --no-ip-access]

域名、证书和已部署的 API 上游默认保持不变。
新安装包里的混淆密钥会一并换上，因为它必须和包内前端一致。
传入 --api 时同时更新上游，并在源码树存在时写回 vite.config.js。
--public-ip 开启或更换公网 IP 访问，--no-ip-access 关闭 IP 访问。都不传时保持原设置。
EOF
}

ARCHIVE=""
CLI_API=""
CLI_PORTAL_SECRET=""
CLI_PUBLIC_IP=""
CLI_NO_IP=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api) CLI_API="${2:-}"; shift 2 ;;
    --portal-secret) CLI_PORTAL_SECRET="${2:-}"; shift 2 ;;
    --public-ip) CLI_PUBLIC_IP="${2:-}"; shift 2 ;;
    --no-ip-access) CLI_NO_IP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      if [[ -z "$ARCHIVE" ]]; then
        ARCHIVE="$1"
        shift
      else
        die "未知参数: $1"
      fi
      ;;
  esac
done

require_root
[[ -n "$ARCHIVE" && -f "$ARCHIVE" ]] || die "请指定安装包路径"
[[ -f /etc/ispweb/ispweb.env ]] || die "尚未安装，请先执行 deploy/install.sh"
[[ -L /opt/ispweb/current ]] || die "找不到 /opt/ispweb/current"

if [[ -f "${ARCHIVE}.sha256" ]]; then
  (
    cd "$(dirname "$ARCHIVE")"
    sha256sum -c "$(basename "${ARCHIVE}.sha256")"
  )
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
tar --no-same-owner --no-same-permissions -xzf "$ARCHIVE" -C "$TMP"
mapfile -d '' -t TOPS < <(find "$TMP" -mindepth 1 -maxdepth 1 -type d -print0)
TOP="${TOPS[0]:-}"
[[ -n "$TOP" && -f "$TOP/dist/index.html" && -f "$TOP/deploy/package.env" ]] || die "安装包内容不完整"

upgrade_from_package_root "$TOP"
