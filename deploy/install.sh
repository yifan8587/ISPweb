#!/usr/bin/env bash
# Ubuntu 22.04 / 24.04 安装 ISPweb：Nginx、证书、URL 混淆网关。
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/release.sh"

usage() {
  cat <<'EOF'
用法:
  sudo ./deploy/install.sh --domain portal.example.com --ssl certbot --email admin@example.com
  sudo ./deploy/install.sh --domain portal.example.com --api http://127.0.0.1:8000 --ssl self-signed
  sudo ./deploy/install.sh --config /root/ispweb-install.env

  --domain       对外域名，必填
  --allow-ip     另外允许用本机公网 IP 经 HTTPS 访问。IP 不在证书里，浏览器会提示证书不受信任
  --public-ip    公网 IP。配合 --allow-ip，NAT 后探测不到时手填
  --api          ISPmanager 门户 API 地址。分机部署写成 https://管理端域名:8443
  --portal-secret 与 ISPmanager 的 PORTAL_API_SECRET 相同。远程 API 必填，至少 32 位
  --ca-file      校验上游证书时额外信任的 CA 或证书文件
  --tls-insecure 不校验上游证书。只在实验室使用
  --ssl          certbot、self-signed、provided
  --email        certbot 注册邮箱
  --ssl-cert     已有证书全链文件，配合 --ssl provided
  --ssl-key      已有私钥，配合 --ssl provided
  --ssl-chain    证书链，提供后开启 OCSP Stapling
  --config       预先写好的配置文件，命令行参数优先
  --with-fail2ban / --without-fail2ban
  --force-os     在 Ubuntu 22.04 / 24.04 以外的系统上继续（仅实验）
  --fresh        机器上已有 ISPweb 时仍按全新安装处理。默认改为原系统升级
EOF
}

CONFIG_FILE=""
CLI_DOMAIN=""
CLI_API=""
CLI_PORTAL_SECRET=""
CLI_CA_FILE=""
CLI_TLS_VERIFY=""
CLI_SSL_MODE=""
CLI_EMAIL=""
CLI_SSL_CERT=""
CLI_SSL_KEY=""
CLI_SSL_TRUSTED=""
CLI_FAIL2BAN=""
CLI_ALLOW_IP=""
CLI_PUBLIC_IP=""
FORCE_OS=0
FRESH_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG_FILE="${2:-}"; shift 2 ;;
    --domain) CLI_DOMAIN="${2:-}"; shift 2 ;;
    --api) CLI_API="${2:-}"; shift 2 ;;
    --portal-secret) CLI_PORTAL_SECRET="${2:-}"; shift 2 ;;
    --ca-file) CLI_CA_FILE="${2:-}"; shift 2 ;;
    --tls-insecure) CLI_TLS_VERIFY=0; shift ;;
    --ssl) CLI_SSL_MODE="${2:-}"; shift 2 ;;
    --email) CLI_EMAIL="${2:-}"; shift 2 ;;
    --ssl-cert) CLI_SSL_CERT="${2:-}"; shift 2 ;;
    --ssl-key) CLI_SSL_KEY="${2:-}"; shift 2 ;;
    --ssl-chain) CLI_SSL_TRUSTED="${2:-}"; shift 2 ;;
    --allow-ip) CLI_ALLOW_IP=1; shift ;;
    --public-ip) CLI_PUBLIC_IP="${2:-}"; CLI_ALLOW_IP=1; shift 2 ;;
    --with-fail2ban) CLI_FAIL2BAN=1; shift ;;
    --without-fail2ban) CLI_FAIL2BAN=0; shift ;;
    --force-os) FORCE_OS=1; shift ;;
    --fresh) FRESH_INSTALL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "未知参数: $1" ;;
  esac
done

require_root
require_supported_ubuntu

if [[ -n "$CONFIG_FILE" ]]; then
  [[ -f "$CONFIG_FILE" ]] || die "找不到配置文件: $CONFIG_FILE"
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi

DOMAIN="${CLI_DOMAIN:-${DOMAIN:-}}"
API="${CLI_API:-${API:-${API_UPSTREAM:-}}}"
SSL_MODE="${CLI_SSL_MODE:-${SSL_MODE:-}}"
EMAIL="${CLI_EMAIL:-${EMAIL:-${CERTBOT_EMAIL:-}}}"
SSL_CERT="${CLI_SSL_CERT:-${SSL_CERT:-}}"
SSL_KEY="${CLI_SSL_KEY:-${SSL_KEY:-}}"
SSL_TRUSTED="${CLI_SSL_TRUSTED:-${SSL_TRUSTED:-}}"
WITH_FAIL2BAN="${CLI_FAIL2BAN:-${WITH_FAIL2BAN:-0}}"
ALLOW_IP_ACCESS="${CLI_ALLOW_IP:-${ALLOW_IP_ACCESS:-0}}"
PUBLIC_IP="${CLI_PUBLIC_IP:-${PUBLIC_IP:-}}"

if [[ -f "$SCRIPT_DIR/package.env" && -f "$SCRIPT_DIR/../dist/index.html" ]]; then
  PKG_ENV="$SCRIPT_DIR/package.env"
  DIST_DIR=$(cd "$SCRIPT_DIR/../dist" && pwd)
elif [[ -f "$SCRIPT_DIR/output/package.env" && -f "$SCRIPT_DIR/../dist/index.html" ]]; then
  PKG_ENV="$SCRIPT_DIR/output/package.env"
  DIST_DIR=$(cd "$SCRIPT_DIR/../dist" && pwd)
else
  die "找不到 dist 或 package.env。请先执行 ./deploy/pack.sh，或在解压后的安装包中运行本脚本"
fi

if [[ "$FRESH_INSTALL" != "1" && -f /etc/ispweb/ispweb.env && -L /opt/ispweb/current ]]; then
  log "检测到已安装的 ISPweb，改为原系统升级。域名、证书和已生效的 API 上游保持不变"
  PACKAGE_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
  UPGRADE_STAGE=""
  if [[ ! -f "$PACKAGE_ROOT/deploy/package.env" ]]; then
    UPGRADE_STAGE=$(mktemp -d)
    mkdir -p "$UPGRADE_STAGE/dist" "$UPGRADE_STAGE/deploy"
    cp -a "$DIST_DIR/." "$UPGRADE_STAGE/dist/"
    tar -C "$SCRIPT_DIR" --exclude output --exclude package.env --exclude __pycache__ --exclude '*.pyc' -cf - . | tar -C "$UPGRADE_STAGE/deploy" -xf -
    cp "$PKG_ENV" "$UPGRADE_STAGE/deploy/package.env"
    PACKAGE_ROOT="$UPGRADE_STAGE"
  fi
  upgrade_from_package_root "$PACKAGE_ROOT"
  if [[ -n "$UPGRADE_STAGE" ]]; then
    rm -rf "$UPGRADE_STAGE"
  fi
  exit 0
fi

SAVED_DOMAIN="$DOMAIN"
SAVED_API="$API"
SAVED_SSL_MODE="$SSL_MODE"
SAVED_EMAIL="$EMAIL"
SAVED_SSL_CERT="$SSL_CERT"
SAVED_SSL_KEY="$SSL_KEY"
SAVED_SSL_TRUSTED="$SSL_TRUSTED"
SAVED_PUBLIC_IP="$PUBLIC_IP"
load_env_file "$PKG_ENV"
URL_GUARD_SECRET="${URL_GUARD_SECRET:-}"
[[ -n "$URL_GUARD_SECRET" ]] || die "安装包缺少 URL_GUARD_SECRET"
PACKAGE_API="${API_UPSTREAM:-}"
DOMAIN="$SAVED_DOMAIN"
API="$SAVED_API"
SSL_MODE="$SAVED_SSL_MODE"
EMAIL="$SAVED_EMAIL"
SSL_CERT="$SAVED_SSL_CERT"
SSL_KEY="$SAVED_SSL_KEY"
SSL_TRUSTED="$SAVED_SSL_TRUSTED"
PUBLIC_IP="$SAVED_PUBLIC_IP"

if [[ -z "$API" && -f /etc/ispweb/ispweb.env ]]; then
  API=$(env_get /etc/ispweb/ispweb.env API_UPSTREAM || true)
fi
if [[ -z "$API" ]]; then
  API="$PACKAGE_API"
fi
if [[ -z "$DOMAIN" && -f /etc/ispweb/ispweb.env ]]; then
  DOMAIN=$(env_get /etc/ispweb/ispweb.env DOMAIN || true)
fi
if [[ -z "$SSL_MODE" && -f /etc/ispweb/ispweb.env ]]; then
  SSL_MODE=$(env_get /etc/ispweb/ispweb.env SSL_MODE || true)
fi

if [[ -z "$DOMAIN" ]]; then
  [[ -t 0 ]] || die "请通过 --domain 指定域名"
  read -r -p "访问域名: " DOMAIN
fi
if [[ -z "$SSL_MODE" ]]; then
  [[ -t 0 ]] || die "请通过 --ssl 指定 certbot、self-signed 或 provided"
  echo "证书方式: 1) certbot  2) self-signed  3) provided"
  read -r -p "请选择 [1/2/3]: " SSL_CHOICE
  case "$SSL_CHOICE" in
    1) SSL_MODE=certbot ;;
    2) SSL_MODE=self-signed ;;
    3) SSL_MODE=provided ;;
    *) die "无法识别的证书方式" ;;
  esac
fi

DOMAIN=$(python3 "$SCRIPT_DIR/lib/project_config.py" validate-domain "$DOMAIN")
if [[ "$ALLOW_IP_ACCESS" == "1" ]]; then
  if [[ -z "$PUBLIC_IP" ]]; then
    PUBLIC_IP=$(detect_public_ip) || die "探测不到公网 IP，请用 --public-ip 指定"
  fi
  PUBLIC_IP=$(python3 "$SCRIPT_DIR/lib/project_config.py" validate-ip "$PUBLIC_IP")
else
  PUBLIC_IP=""
fi
API_UPSTREAM=$(python3 "$SCRIPT_DIR/lib/project_config.py" validate-api "$API")
PORTAL_API_SECRET="${CLI_PORTAL_SECRET:-${PORTAL_API_SECRET:-}}"
if [[ -z "$PORTAL_API_SECRET" && -f /etc/ispweb/ispweb.env ]]; then
  PORTAL_API_SECRET=$(env_get /etc/ispweb/ispweb.env PORTAL_API_SECRET || true)
fi
URL_GUARD_CA_FILE="${CLI_CA_FILE:-${URL_GUARD_CA_FILE:-${CA_FILE:-}}}"
if [[ -n "$CLI_TLS_VERIFY" ]]; then
  URL_GUARD_TLS_VERIFY="$CLI_TLS_VERIFY"
else
  URL_GUARD_TLS_VERIFY="${URL_GUARD_TLS_VERIFY:-${TLS_VERIFY:-1}}"
fi
if [[ "$(python3 "$SCRIPT_DIR/lib/project_config.py" api-is-loopback "$API_UPSTREAM")" != "yes" ]]; then
  [[ ${#PORTAL_API_SECRET} -ge 32 ]] || die "远程 API 必须通过 --portal-secret 提供至少 32 位密钥，并与 ISPmanager 的 PORTAL_API_SECRET 相同"
fi
if [[ -n "$URL_GUARD_CA_FILE" && ! -f "$URL_GUARD_CA_FILE" ]]; then
  die "找不到证书文件: $URL_GUARD_CA_FILE"
fi
case "$SSL_MODE" in
  certbot|self-signed|provided) ;;
  *) die "证书方式只能是 certbot、self-signed 或 provided" ;;
esac
if [[ "$SSL_MODE" == "certbot" && -z "$EMAIL" ]]; then
  [[ -t 0 ]] || die "certbot 需要 --email"
  read -r -p "证书通知邮箱: " EMAIL
fi
if [[ "$SSL_MODE" == "provided" ]]; then
  [[ -n "$SSL_CERT" && -f "$SSL_CERT" ]] || die "请通过 --ssl-cert 提供证书文件"
  [[ -n "$SSL_KEY" && -f "$SSL_KEY" ]] || die "请通过 --ssl-key 提供私钥文件"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx python3 openssl ca-certificates ssl-cert curl
if [[ "$SSL_MODE" == "certbot" ]]; then
  apt-get install -y certbot
fi

ensure_service_user
install -d -m 755 /opt/ispweb/releases /var/www/html /etc/nginx/snippets /etc/ispweb/ssl
RELEASE="/opt/ispweb/releases/rel-$(date +%Y%m%d%H%M%S)"
mkdir -p "$RELEASE/dist" "$RELEASE/deploy"
cp -a "$DIST_DIR/." "$RELEASE/dist/"
tar -C "$SCRIPT_DIR" --exclude output --exclude package.env --exclude __pycache__ --exclude '*.pyc' -cf - . | tar -C "$RELEASE/deploy" -xf -
cp "$PKG_ENV" "$RELEASE/deploy/package.env"
apply_tree_perms "$RELEASE"
ln -sfn "$RELEASE" /opt/ispweb/current
sync_vite_api

install_security_conf
write_runtime_env

if [[ "$SSL_MODE" == "certbot" ]]; then
  render_nginx_site bootstrap
  nginx_apply
  certbot certonly --webroot -w /var/www/html -d "$DOMAIN" \
    --email "$EMAIL" --agree-tos --non-interactive --keep-until-expiring
  SSL_CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  SSL_KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
  SSL_TRUSTED="/etc/letsencrypt/live/${DOMAIN}/chain.pem"
elif [[ "$SSL_MODE" == "self-signed" ]]; then
  SELF_SIGNED_ID="${DOMAIN}${PUBLIC_IP:+ ${PUBLIC_IP}}"
  if [[ ! -f /etc/ispweb/ssl/fullchain.pem || "$(cat /etc/ispweb/ssl/domain 2>/dev/null || true)" != "$SELF_SIGNED_ID" ]]; then
    openssl req -x509 -nodes -newkey rsa:2048 \
      -keyout /etc/ispweb/ssl/privkey.pem \
      -out /etc/ispweb/ssl/fullchain.pem \
      -days 825 \
      -subj "/CN=${DOMAIN}" \
      -addext "subjectAltName=DNS:${DOMAIN}${PUBLIC_IP:+,IP:${PUBLIC_IP}}"
    printf '%s\n' "$SELF_SIGNED_ID" > /etc/ispweb/ssl/domain
  fi
  chown root:www-data /etc/ispweb/ssl/privkey.pem
  chmod 640 /etc/ispweb/ssl/privkey.pem
  chmod 644 /etc/ispweb/ssl/fullchain.pem
  SSL_CERT=/etc/ispweb/ssl/fullchain.pem
  SSL_KEY=/etc/ispweb/ssl/privkey.pem
  SSL_TRUSTED=""
else
  install -m 644 "$SSL_CERT" /etc/ispweb/ssl/fullchain.pem
  install -m 640 -o root -g www-data "$SSL_KEY" /etc/ispweb/ssl/privkey.pem
  SSL_CERT=/etc/ispweb/ssl/fullchain.pem
  SSL_KEY=/etc/ispweb/ssl/privkey.pem
  if [[ -n "$SSL_TRUSTED" ]]; then
    install -m 644 "$SSL_TRUSTED" /etc/ispweb/ssl/chain.pem
    SSL_TRUSTED=/etc/ispweb/ssl/chain.pem
  fi
fi

prepare_upstream_trust
write_runtime_env
render_nginx_site full
nginx_apply
install_gateway_unit
wait_gateway || die "访问网关未通过健康检查"

if [[ "$WITH_FAIL2BAN" == "1" ]]; then
  apt-get install -y fail2ban
  install -m 644 /opt/ispweb/current/deploy/nginx/fail2ban-filter.conf /etc/fail2ban/filter.d/ispweb-nginx.conf
  install -m 644 /opt/ispweb/current/deploy/nginx/fail2ban-jail.conf /etc/fail2ban/jail.d/ispweb.conf
  systemctl enable --now fail2ban
  systemctl reload fail2ban || systemctl restart fail2ban
fi

log "安装完成"
log "访问地址: https://${DOMAIN}/"
if [[ -n "$PUBLIC_IP" ]]; then
  log "IP 访问: https://${PUBLIC_IP}/（证书不含该 IP 时浏览器会提示不受信任）"
fi
log "API 上游: ${API_UPSTREAM}"
log "证书方式: ${SSL_MODE}"
log "混淆密钥指纹: $(secret_fingerprint "$URL_GUARD_SECRET")"
if [[ -n "${PORTAL_API_SECRET:-}" ]]; then
  log "门户 API 密钥指纹: $(secret_fingerprint "$PORTAL_API_SECRET")"
fi
log "请把域名 A/AAAA 记录指到这台服务器，并确认 ISPmanager 已监听 ${API_UPSTREAM}"
if [[ "$SSL_MODE" == "self-signed" ]]; then
  log "当前是自签证书，浏览器会提示不受信任。正式环境请改用 certbot 或企业证书后重新执行本脚本"
fi
if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  log "已在启用的 ufw 中放行 80 和 443"
else
  log "若启用防火墙，请放行 TCP 80 和 TCP 443。本脚本不会主动打开 ufw"
fi
