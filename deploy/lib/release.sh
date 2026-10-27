#!/usr/bin/env bash
# 安装与更新共用的发布目录、权限和 Nginx 渲染。

apply_tree_perms() {
  local dest="$1"
  chmod 755 /opt/ispweb /opt/ispweb/releases "$dest"
  chown -R root:www-data "$dest/dist"
  find "$dest/dist" -type d -exec chmod 755 {} \;
  find "$dest/dist" -type f -exec chmod 644 {} \;
  chown -R root:ispweb "$dest/deploy"
  find "$dest/deploy" -type d -exec chmod 750 {} \;
  find "$dest/deploy" -type f -exec chmod 640 {} \;
  find "$dest/deploy" -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod 750 {} \;
}

ensure_service_user() {
  if ! getent group ispweb >/dev/null; then
    groupadd --system ispweb
  fi
  if ! id ispweb >/dev/null 2>&1; then
    useradd --system --home-dir /opt/ispweb --shell /usr/sbin/nologin --gid ispweb ispweb
  fi
}

write_runtime_env() {
  local previous
  previous=$(umask)
  install -d -m 711 /etc/ispweb
  install -d -m 755 /etc/ispweb/ssl
  umask 077
  cat > /etc/ispweb/ispweb.env <<EOF
DOMAIN=${DOMAIN}
PUBLIC_IP=${PUBLIC_IP:-}
API_UPSTREAM=${API_UPSTREAM}
SSL_MODE=${SSL_MODE}
SSL_CERT=${SSL_CERT}
SSL_KEY=${SSL_KEY}
SSL_TRUSTED=${SSL_TRUSTED:-}
URL_GUARD_SECRET=${URL_GUARD_SECRET}
URL_GUARD_BIND=127.0.0.1
URL_GUARD_PORT=8765
URL_GUARD_SKEW=${URL_GUARD_SKEW:-120}
URL_GUARD_STRICT=1
URL_GUARD_MAX_BODY=2097152
PORTAL_API_SECRET=${PORTAL_API_SECRET:-}
URL_GUARD_TLS_VERIFY=${URL_GUARD_TLS_VERIFY:-1}
URL_GUARD_CA_FILE=${URL_GUARD_CA_FILE:-}
URL_GUARD_TLS_NAME=${URL_GUARD_TLS_NAME:-}
WEB_ROOT=/opt/ispweb/current/dist
EOF
  chmod 600 /etc/ispweb/ispweb.env
  chown root:root /etc/ispweb/ispweb.env
  umask "$previous"
}

prepare_upstream_trust() {
  local info key value
  URL_GUARD_TLS_VERIFY="${URL_GUARD_TLS_VERIFY:-1}"
  info=$(python3 "$SCRIPT_DIR/lib/upstream_trust.py" \
    --api "$API_UPSTREAM" \
    --ca-file "${URL_GUARD_CA_FILE:-}" \
    --pin-path /etc/ispweb/ssl/upstream.pem \
    --verify "$URL_GUARD_TLS_VERIFY")
  URL_GUARD_CA_FILE=""
  URL_GUARD_TLS_NAME=""
  while IFS='=' read -r key value; do
    case "$key" in
      CA_FILE) URL_GUARD_CA_FILE="$value" ;;
      TLS_NAME) URL_GUARD_TLS_NAME="$value" ;;
      FINGERPRINT)
        if [[ -n "$value" ]]; then
          log "管理端证书指纹: ${value}"
        fi
        ;;
      MODE)
        case "$value" in
          pinned) log "管理端证书不受公共 CA 信任，已钉住。网关只接受这张证书" ;;
          system) log "管理端证书由公共 CA 信任" ;;
          provided) log "管理端证书使用指定的 CA 文件校验" ;;
          insecure) log "已关闭管理端证书校验" ;;
        esac
        ;;
    esac
  done <<< "$info"
}

install_security_conf() {
  install -d -m 755 /etc/nginx/conf.d /etc/nginx/snippets
  install -m 644 /opt/ispweb/current/deploy/nginx/ispweb-security.conf /etc/nginx/conf.d/ispweb-security.conf
}

render_nginx_site() {
  local mode="$1"
  local py="/opt/ispweb/current/deploy/lib/render_nginx.py"
  local -a args=(
    --mode "$mode"
    --domain "$DOMAIN"
    --api "$API_UPSTREAM"
    --web-root /opt/ispweb/current/dist
    --guard-port 8765
    --out /etc/nginx/sites-available/ispweb.conf
  )
  if ipv6_enabled; then
    args+=(--ipv6)
  fi
  if [[ -n "${PUBLIC_IP:-}" ]]; then
    args+=(--public-ip "$PUBLIC_IP")
  fi
  if [[ "$mode" == "full" ]]; then
    args+=(--ssl-cert "$SSL_CERT" --ssl-key "$SSL_KEY" --headers-out /etc/nginx/snippets/ispweb-headers.conf)
    if [[ -n "${SSL_TRUSTED:-}" ]]; then
      args+=(--ssl-trusted "$SSL_TRUSTED" --stapling)
    fi
    if [[ "${SSL_MODE}" != "self-signed" ]]; then
      args+=(--hsts)
    fi
  fi
  python3 "$py" "${args[@]}"
  ln -sfn /etc/nginx/sites-available/ispweb.conf /etc/nginx/sites-enabled/ispweb.conf
}

nginx_apply() {
  if [[ -e /etc/nginx/sites-enabled/default && ! -e /run/ispweb-default-site.bak ]]; then
    cp -a /etc/nginx/sites-enabled/default /run/ispweb-default-site.bak
  fi
  rm -f /etc/nginx/sites-enabled/default
  if ! nginx -t; then
    if [[ -e /run/ispweb-default-site.bak ]]; then
      cp -a /run/ispweb-default-site.bak /etc/nginx/sites-enabled/default
    fi
    return 1
  fi
  systemctl enable nginx >/dev/null
  systemctl reload nginx || systemctl restart nginx
}

install_gateway_unit() {
  install -m 644 /opt/ispweb/current/deploy/gate/ispweb-urlguard.service /etc/systemd/system/ispweb-urlguard.service
  systemctl daemon-reload
  systemctl enable ispweb-urlguard.service >/dev/null
  systemctl restart ispweb-urlguard.service
}

wait_gateway() {
  local attempt
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS --max-time 2 http://127.0.0.1:8765/healthz >/dev/null; then
      return 0
    fi
    sleep 0.3
  done
  journalctl -u ispweb-urlguard -n 40 --no-pager || true
  return 1
}

sync_vite_api() {
  local vite="$SCRIPT_DIR/../vite.config.js"
  local pkg="$SCRIPT_DIR/../package.json"
  if [[ -f "$vite" && -f "$pkg" ]]; then
    python3 "$SCRIPT_DIR/lib/project_config.py" set-vite "$vite" "$API_UPSTREAM" >/dev/null
    log "已把 API 地址写入 vite.config.js：${API_UPSTREAM}"
  fi
}

# 用一份已解压的安装包替换正在运行的版本。域名、证书和已生效的 API 上游保持不变。
upgrade_from_package_root() {
  local src="$1"
  local new_secret package_api old_current env_backup site_backup head_backup
  [[ -d "$src" && -f "$src/dist/index.html" && -f "$src/deploy/package.env" ]] || die "安装包内容不完整"
  [[ -f /etc/ispweb/ispweb.env ]] || die "尚未安装，请先执行 deploy/install.sh"
  [[ -L /opt/ispweb/current ]] || die "找不到 /opt/ispweb/current"

  load_env_file "$src/deploy/package.env"
  new_secret="$URL_GUARD_SECRET"
  package_api="$API_UPSTREAM"
  [[ -n "$new_secret" ]] || die "安装包缺少 URL_GUARD_SECRET"

  DOMAIN=$(env_get /etc/ispweb/ispweb.env DOMAIN)
  SSL_MODE=$(env_get /etc/ispweb/ispweb.env SSL_MODE)
  SSL_CERT=$(env_get /etc/ispweb/ispweb.env SSL_CERT)
  SSL_KEY=$(env_get /etc/ispweb/ispweb.env SSL_KEY)
  SSL_TRUSTED=$(env_get /etc/ispweb/ispweb.env SSL_TRUSTED || true)
  URL_GUARD_SKEW=$(env_get /etc/ispweb/ispweb.env URL_GUARD_SKEW || true)
  API_UPSTREAM=$(env_get /etc/ispweb/ispweb.env API_UPSTREAM)
  PORTAL_API_SECRET=$(env_get /etc/ispweb/ispweb.env PORTAL_API_SECRET || true)
  URL_GUARD_TLS_VERIFY=$(env_get /etc/ispweb/ispweb.env URL_GUARD_TLS_VERIFY || true)
  URL_GUARD_CA_FILE=$(env_get /etc/ispweb/ispweb.env URL_GUARD_CA_FILE || true)
  URL_GUARD_TLS_NAME=$(env_get /etc/ispweb/ispweb.env URL_GUARD_TLS_NAME || true)
  PUBLIC_IP=$(env_get /etc/ispweb/ispweb.env PUBLIC_IP || true)
  if [[ "${CLI_NO_IP:-0}" == "1" ]]; then
    PUBLIC_IP=""
  elif [[ -n "${CLI_PUBLIC_IP:-}" ]]; then
    PUBLIC_IP=$(python3 "$src/deploy/lib/project_config.py" validate-ip "$CLI_PUBLIC_IP")
  fi
  if [[ -n "${CLI_API:-}" ]]; then
    API_UPSTREAM=$(python3 "$src/deploy/lib/project_config.py" validate-api "$CLI_API")
  elif [[ -z "$API_UPSTREAM" ]]; then
    API_UPSTREAM=$(python3 "$src/deploy/lib/project_config.py" validate-api "$package_api")
  fi
  if [[ -n "${CLI_PORTAL_SECRET:-}" ]]; then
    PORTAL_API_SECRET="$CLI_PORTAL_SECRET"
  fi
  if [[ "$(python3 "$src/deploy/lib/project_config.py" api-is-loopback "$API_UPSTREAM")" != "yes" ]]; then
    [[ ${#PORTAL_API_SECRET} -ge 32 ]] || die "远程 API 需要已保存的 PORTAL_API_SECRET，或通过 --portal-secret 传入"
  fi
  URL_GUARD_SECRET="$new_secret"
  DOMAIN=$(python3 "$src/deploy/lib/project_config.py" validate-domain "$DOMAIN")
  [[ -f "$SSL_CERT" && -f "$SSL_KEY" ]] || die "现有证书文件不存在，请重新执行 install.sh"

  old_current=$(readlink -f /opt/ispweb/current)
  env_backup=$(mktemp)
  site_backup=$(mktemp)
  head_backup=$(mktemp)
  cp /etc/ispweb/ispweb.env "$env_backup"
  cp /etc/nginx/sites-available/ispweb.conf "$site_backup"
  if [[ -f /etc/nginx/snippets/ispweb-headers.conf ]]; then
    cp /etc/nginx/snippets/ispweb-headers.conf "$head_backup"
  fi

  RELEASE="/opt/ispweb/releases/rel-$(date +%Y%m%d%H%M%S)"
  mkdir -p "$RELEASE"
  cp -a "$src/." "$RELEASE/"
  apply_tree_perms "$RELEASE"
  ln -sfn "$RELEASE" /opt/ispweb/current
  if [[ -n "${CLI_API:-}" ]]; then
    sync_vite_api
  fi

  rollback_upgrade() {
    log "更新未完成，正在回滚"
    cp "$env_backup" /etc/ispweb/ispweb.env
    chmod 600 /etc/ispweb/ispweb.env
    cp "$site_backup" /etc/nginx/sites-available/ispweb.conf
    if [[ -s "$head_backup" ]]; then
      cp "$head_backup" /etc/nginx/snippets/ispweb-headers.conf
    fi
    ln -sfn "$old_current" /opt/ispweb/current
    systemctl restart ispweb-urlguard.service || true
    nginx -t && systemctl reload nginx || true
  }

  if ! prepare_upstream_trust; then
    rollback_upgrade
    die "无法校验管理端 API 证书"
  fi
  write_runtime_env
  install_security_conf
  if ! render_nginx_site full; then
    rollback_upgrade
    die "渲染 Nginx 配置失败"
  fi
  if ! nginx -t; then
    rollback_upgrade
    die "Nginx 配置检查失败"
  fi
  if ! install_gateway_unit; then
    rollback_upgrade
    die "访问网关启动失败"
  fi
  if ! nginx_apply; then
    rollback_upgrade
    die "Nginx 重载失败"
  fi
  if ! wait_gateway; then
    rollback_upgrade
    die "访问网关健康检查失败"
  fi

  local current_real index dir
  current_real=$(readlink -f /opt/ispweb/current)
  mapfile -t RELEASES < <(ls -1dt /opt/ispweb/releases/* 2>/dev/null || true)
  index=0
  for dir in "${RELEASES[@]}"; do
    index=$((index + 1))
    if [[ "$index" -le 3 ]]; then
      continue
    fi
    if [[ "$(readlink -f "$dir")" == "$current_real" || "$(readlink -f "$dir")" == "$old_current" ]]; then
      continue
    fi
    rm -rf "$dir"
  done

  log "更新完成: https://${DOMAIN}/"
  if [[ -n "${PUBLIC_IP:-}" ]]; then
    log "IP 访问: https://${PUBLIC_IP}/"
  fi
  log "API 上游: ${API_UPSTREAM}"
  log "混淆密钥指纹: $(secret_fingerprint "$URL_GUARD_SECRET")"
  if [[ -n "${PORTAL_API_SECRET:-}" ]]; then
    log "门户 API 密钥指纹: $(secret_fingerprint "$PORTAL_API_SECRET")"
  fi
  log "上一版本仍保留在 ${old_current}。如需手动退回，把 /opt/ispweb/current 指回该目录后重启 ispweb-urlguard 并重载 Nginx"
}
