#!/usr/bin/env bash
# 在构建机打包 ISPweb 安装包。需要 Node.js 18+。
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"
ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

usage() {
  cat <<'EOF'
用法: ./deploy/pack.sh [--api http://127.0.0.1:8000]

读取或改写 vite.config.js 中的 API 地址，开启 URL 混淆后构建前端，
并在 deploy/output/ 生成安装包。安装包内含与本次构建绑定的签名密钥。
EOF
}

API=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api) API="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "未知参数: $1" ;;
  esac
done

cd "$ROOT"
command -v node >/dev/null || die "需要 Node.js 18 或更高版本"
command -v npm >/dev/null || die "需要 npm"
command -v python3 >/dev/null || die "需要 python3"
command -v openssl >/dev/null || die "需要 openssl"
NODE_MAJOR=$(node -p 'Number(process.versions.node.split(".")[0])')
[[ "$NODE_MAJOR" -ge 18 ]] || die "需要 Node.js 18 或更高版本，当前为 $(node -v)"

if [[ -z "$API" ]]; then
  API=$(python3 - <<'PY'
import re
from pathlib import Path
text = Path("vite.config.js").read_text(encoding="utf-8")
match = re.search(r"VITE_API_PROXY_TARGET \|\| '([^']*)'", text)
print(match.group(1) if match else "")
PY
)
fi
API=$(python3 "$SCRIPT_DIR/lib/project_config.py" validate-api "$API")
python3 "$SCRIPT_DIR/lib/project_config.py" set-vite "$ROOT/vite.config.js" "$API" >/dev/null
export VITE_API_PROXY_TARGET="$API"
log "API 地址已写入 vite.config.js：${API}"

SECRET=$(openssl rand -hex 32)
umask 077
cat > "$ROOT/.env.deploy.local" <<EOF
VITE_URL_GUARD=1
VITE_URL_GUARD_SECRET=${SECRET}
EOF
chmod 600 "$ROOT/.env.deploy.local"
umask 022

if [[ ! -d "$ROOT/node_modules" ]]; then
  if [[ -f "$ROOT/package-lock.json" ]]; then
    npm ci
  else
    npm install
  fi
fi
npx vite build --mode deploy
[[ -f "$ROOT/dist/index.html" ]] || die "构建未生成 dist/index.html"

VERSION=$(python3 -c 'import json; print(json.load(open("package.json", encoding="utf-8"))["version"])')
STAMP=$(date +%Y%m%d%H%M%S)
NAME="ispweb-${VERSION}-${STAMP}"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
PKG="$STAGE/$NAME"
mkdir -p "$PKG/dist" "$PKG/deploy" "$SCRIPT_DIR/output"
cp -a "$ROOT/dist/." "$PKG/dist/"
tar -C "$SCRIPT_DIR" --exclude output --exclude package.env --exclude __pycache__ --exclude '*.pyc' -cf - . | tar -C "$PKG/deploy" -xf -
if [[ -d "$ROOT/ReadMe" ]]; then
  cp -a "$ROOT/ReadMe" "$PKG/ReadMe"
fi
cat > "$PKG/deploy/package.env" <<EOF
# 与本次前端构建绑定。更新时必须连同 dist 一起替换。
APP_NAME=ispweb
APP_VERSION=${VERSION}
APP_STAMP=${STAMP}
API_UPSTREAM=${API}
URL_GUARD_SECRET=${SECRET}
URL_GUARD_SKEW=120
EOF
chmod 600 "$PKG/deploy/package.env"

ARCHIVE="$SCRIPT_DIR/output/${NAME}.tar.gz"
tar -C "$STAGE" -czf "$ARCHIVE" "$NAME"
chmod 600 "$ARCHIVE"
(
  cd "$SCRIPT_DIR/output"
  sha256sum "${NAME}.tar.gz" > "${NAME}.tar.gz.sha256"
  chmod 600 "${NAME}.tar.gz.sha256"
)
cp "$PKG/deploy/package.env" "$SCRIPT_DIR/output/package.env"
chmod 600 "$SCRIPT_DIR/output/package.env"

log "安装包: ${ARCHIVE}"
log "校验文件: ${ARCHIVE}.sha256"
log "混淆密钥指纹: $(secret_fingerprint "$SECRET")"
log "把安装包传到 Ubuntu 22.04 / 24.04 后执行: sudo ./deploy/install.sh --domain 你的域名 --api https://管理端域名:8443 --portal-secret 密钥 --ssl certbot --email 你的邮箱"
