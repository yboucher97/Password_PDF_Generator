#!/usr/bin/env bash
set -euo pipefail

APP_NAME="password-pdf-generator"
SERVICE_NAME="${PASSWORD_PDF_SERVICE_NAME:-password-pdf-generator}"
SERVICE_USER="${PASSWORD_PDF_SERVICE_USER:-passwordpdf}"
INSTALL_DIR="${PASSWORD_PDF_INSTALL_DIR:-/opt/password-pdf-generator}"
DATA_DIR="${PASSWORD_PDF_DATA_DIR:-/var/lib/password-pdf-generator}"
CONFIG_DIR="${PASSWORD_PDF_CONFIG_DIR:-/etc/password-pdf-generator}"
CONFIG_PATH="${CONFIG_DIR}/brand_settings.json"
ENV_FILE="${PASSWORD_PDF_ENV_FILE:-/etc/password-pdf-generator.env}"
META_FILE="${PASSWORD_PDF_META_FILE:-${CONFIG_DIR}/install-meta.env}"
REPO_URL="${PASSWORD_PDF_REPO_URL:-https://github.com/yboucher97/Password_PDF_Generator.git}"
REPO_REF="${PASSWORD_PDF_REPO_REF:-main}"
PORT="${PASSWORD_PDF_PORT:-8000}"
HOST="${PASSWORD_PDF_HOST:-}"
API_KEY="${PASSWORD_PDF_API_KEY:-${WIFI_PDF_API_KEY:-}}"
ENABLE_WORKDRIVE="${PASSWORD_PDF_ENABLE_WORKDRIVE:-}"
ZOHO_REGION="${PASSWORD_PDF_ZOHO_REGION:-com}"
UFW_MODE="${PASSWORD_PDF_CONFIGURE_UFW:-auto}"
INSTALL_OWNER="${PASSWORD_PDF_INSTALL_OWNER:-${SUDO_USER:-$(id -un)}}"
INSTALL_OWNER_HOME="${PASSWORD_PDF_OWNER_HOME:-}"
PATHS_FILE="${PASSWORD_PDF_PATHS_FILE:-}"

log() {
  printf '[%s] %s\n' "${APP_NAME}" "$*"
}

fail() {
  printf '[%s] ERROR: %s\n' "${APP_NAME}" "$*" >&2
  exit 1
}

generate_secret() {
  od -An -N32 -tx1 /dev/urandom | tr -d ' \n'
}

initialize_context() {
  if [[ -z "$INSTALL_OWNER_HOME" ]]; then
    if command -v getent >/dev/null 2>&1; then
      INSTALL_OWNER_HOME="$(getent passwd "$INSTALL_OWNER" | cut -d: -f6 || true)"
    fi
    if [[ -z "$INSTALL_OWNER_HOME" ]]; then
      if [[ "$INSTALL_OWNER" == "root" ]]; then
        INSTALL_OWNER_HOME="/root"
      else
        INSTALL_OWNER_HOME="/home/${INSTALL_OWNER}"
      fi
    fi
  fi

  if [[ -z "$PATHS_FILE" ]]; then
    PATHS_FILE="${INSTALL_OWNER_HOME}/${APP_NAME}-paths.txt"
  fi
}

prompt() {
  local var_name="$1"
  local message="$2"
  local secret="${3:-false}"
  local default_value="${4:-}"
  local current_value="${!var_name:-}"

  if [[ -n "${current_value}" ]]; then
    return
  fi

  if [[ ! -t 0 ]]; then
    printf -v "$var_name" '%s' "$default_value"
    return
  fi

  local answer
  if [[ "$secret" == "true" ]]; then
    if [[ -n "$default_value" ]]; then
      read -r -s -p "${message} [press Enter to use generated value]: " answer
      printf '\n'
      printf -v "$var_name" '%s' "${answer:-$default_value}"
    else
      read -r -s -p "${message}: " answer
      printf '\n'
      printf -v "$var_name" '%s' "$answer"
    fi
  else
    if [[ -n "$default_value" ]]; then
      read -r -p "${message} [${default_value}]: " answer
      printf -v "$var_name" '%s' "${answer:-$default_value}"
    else
      read -r -p "${message}: " answer
      printf -v "$var_name" '%s' "$answer"
    fi
  fi
}

prompt_yes_no() {
  local var_name="$1"
  local message="$2"
  local default_value="${3:-false}"
  local current_value="${!var_name:-}"

  if [[ -n "$current_value" ]]; then
    return
  fi

  if [[ ! -t 0 ]]; then
    printf -v "$var_name" '%s' "$default_value"
    return
  fi

  local suffix="y/N"
  if [[ "$default_value" == "true" ]]; then
    suffix="Y/n"
  fi

  local answer
  read -r -p "${message} [${suffix}]: " answer
  answer="${answer,,}"
  case "$answer" in
    y|yes) printf -v "$var_name" '%s' "true" ;;
    n|no) printf -v "$var_name" '%s' "false" ;;
    "") printf -v "$var_name" '%s' "$default_value" ;;
    *) fail "Invalid response for ${message}" ;;
  esac
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    fail "Run this installer as root. Example: sudo bash <(curl -fsSL https://raw.githubusercontent.com/yboucher97/Password_PDF_Generator/main/install.sh)"
  fi
}

ensure_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y git curl ca-certificates openssl python3 python3-venv python3-pip caddy ufw
}

ensure_user_and_dirs() {
  if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --create-home --home "$DATA_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
  fi

  mkdir -p "$DATA_DIR" "$CONFIG_DIR"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
}

sync_repo() {
  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    log "Updating existing repo in ${INSTALL_DIR}"
    git -C "$INSTALL_DIR" fetch --prune origin
    git -C "$INSTALL_DIR" checkout "$REPO_REF"
    git -C "$INSTALL_DIR" reset --hard "origin/${REPO_REF}"
  else
    log "Cloning repo into ${INSTALL_DIR}"
    rm -rf "$INSTALL_DIR"
    git clone --branch "$REPO_REF" "$REPO_URL" "$INSTALL_DIR"
  fi
}

install_python_deps() {
  python3 -m venv "${INSTALL_DIR}/.venv"
  "${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
  "${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
}

configure_runtime_json() {
  local workdrive_api_base
  local workdrive_accounts_base

  case "$ZOHO_REGION" in
    com)
      workdrive_api_base="https://www.zohoapis.com/workdrive/api/v1"
      workdrive_accounts_base="https://accounts.zoho.com/oauth/v2/token"
      ;;
    eu)
      workdrive_api_base="https://www.zohoapis.eu/workdrive/api/v1"
      workdrive_accounts_base="https://accounts.zoho.eu/oauth/v2/token"
      ;;
    in)
      workdrive_api_base="https://www.zohoapis.in/workdrive/api/v1"
      workdrive_accounts_base="https://accounts.zoho.in/oauth/v2/token"
      ;;
    com.au)
      workdrive_api_base="https://www.zohoapis.com.au/workdrive/api/v1"
      workdrive_accounts_base="https://accounts.zoho.com.au/oauth/v2/token"
      ;;
    *)
      fail "Unsupported PASSWORD_PDF_ZOHO_REGION: ${ZOHO_REGION}"
      ;;
  esac

  if [[ ! -f "$CONFIG_PATH" ]]; then
    cp "${INSTALL_DIR}/config/wifi_pdf/brand_settings.json" "$CONFIG_PATH"
  fi

  DATA_OUTPUT_DIR="${DATA_DIR}/output/pdf/wifi" \
  CONFIG_PATH="$CONFIG_PATH" \
  WORKDRIVE_ENABLED="$ENABLE_WORKDRIVE" \
  WORKDRIVE_API_BASE="$workdrive_api_base" \
  WORKDRIVE_ACCOUNTS_BASE="$workdrive_accounts_base" \
  DEFAULT_WORKDRIVE_FOLDER_ID="${ZOHO_WORKDRIVE_PARENT_FOLDER_ID:-}" \
  python3 - <<'PY'
import json
import os
from pathlib import Path

config_path = Path(os.environ["CONFIG_PATH"])
data = json.loads(config_path.read_text(encoding="utf-8"))
data["output"]["root_dir"] = os.environ["DATA_OUTPUT_DIR"]
data["workdrive"]["enabled"] = os.environ["WORKDRIVE_ENABLED"].lower() == "true"
data["workdrive"]["api_base_url"] = os.environ["WORKDRIVE_API_BASE"]
data["workdrive"]["accounts_base_url"] = os.environ["WORKDRIVE_ACCOUNTS_BASE"]
if os.environ["DEFAULT_WORKDRIVE_FOLDER_ID"]:
    data["workdrive"]["parent_folder_id"] = os.environ["DEFAULT_WORKDRIVE_FOLDER_ID"]
config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

write_env_file() {
  if [[ -z "$API_KEY" ]]; then
    API_KEY="$(generate_secret)"
  fi

  ENV_FILE="$ENV_FILE" \
  WIFI_PDF_API_KEY="$API_KEY" \
  ZOHO_WORKDRIVE_CLIENT_ID="${ZOHO_WORKDRIVE_CLIENT_ID:-}" \
  ZOHO_WORKDRIVE_CLIENT_SECRET="${ZOHO_WORKDRIVE_CLIENT_SECRET:-}" \
  ZOHO_WORKDRIVE_REFRESH_TOKEN="${ZOHO_WORKDRIVE_REFRESH_TOKEN:-}" \
  ZOHO_WORKDRIVE_ACCESS_TOKEN="${ZOHO_WORKDRIVE_ACCESS_TOKEN:-}" \
  ZOHO_WORKDRIVE_PARENT_FOLDER_ID="${ZOHO_WORKDRIVE_PARENT_FOLDER_ID:-}" \
  python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["ENV_FILE"])
existing = {}
if path.exists():
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        existing[key] = value

ordered_keys = [
    "WIFI_PDF_API_KEY",
    "ZOHO_WORKDRIVE_CLIENT_ID",
    "ZOHO_WORKDRIVE_CLIENT_SECRET",
    "ZOHO_WORKDRIVE_REFRESH_TOKEN",
    "ZOHO_WORKDRIVE_ACCESS_TOKEN",
    "ZOHO_WORKDRIVE_PARENT_FOLDER_ID",
]

for key in ordered_keys:
    value = os.environ.get(key, "")
    if value:
      existing[key] = value
    elif key not in existing and key == "WIFI_PDF_API_KEY":
      existing[key] = value

lines = []
for key in ordered_keys:
    if key in existing:
        lines.append(f"{key}={existing[key]}")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

  chmod 600 "$ENV_FILE"
  chown root:root "$ENV_FILE"
}

write_install_metadata() {
  mkdir -p "$CONFIG_DIR"
  {
    printf 'SERVICE_NAME=%q\n' "$SERVICE_NAME"
    printf 'SERVICE_USER=%q\n' "$SERVICE_USER"
    printf 'INSTALL_OWNER=%q\n' "$INSTALL_OWNER"
    printf 'INSTALL_DIR=%q\n' "$INSTALL_DIR"
    printf 'DATA_DIR=%q\n' "$DATA_DIR"
    printf 'CONFIG_DIR=%q\n' "$CONFIG_DIR"
    printf 'CONFIG_PATH=%q\n' "$CONFIG_PATH"
    printf 'ENV_FILE=%q\n' "$ENV_FILE"
    printf 'META_FILE=%q\n' "$META_FILE"
    printf 'PATHS_FILE=%q\n' "$PATHS_FILE"
    printf 'HOST=%q\n' "$HOST"
    printf 'PORT=%q\n' "$PORT"
    printf 'REPO_REF=%q\n' "$REPO_REF"
  } >"$META_FILE"
  chmod 644 "$META_FILE"
}

write_paths_file() {
  mkdir -p "$(dirname "$PATHS_FILE")"
  {
    printf '%s  # application code\n' "$INSTALL_DIR"
    printf '%s  # Python virtualenv\n' "${INSTALL_DIR}/.venv"
    printf '%s  # runtime config directory\n' "$CONFIG_DIR"
    printf '%s  # active JSON config\n' "$CONFIG_PATH"
    printf '%s  # secrets environment file\n' "$ENV_FILE"
    printf '%s  # systemd service file\n' "/etc/systemd/system/${SERVICE_NAME}.service"
    printf '%s  # application data root\n' "$DATA_DIR"
    printf '%s  # generated PDFs, manifests, QR images, and logs\n' "${DATA_DIR}/output/pdf/wifi"
    printf '%s  # rotating application log file\n' "${DATA_DIR}/output/pdf/wifi/logs/wifi_pdf.log"
    printf '%s  # local update script\n' "${INSTALL_DIR}/update.sh"
    if [[ -n "$HOST" ]]; then
      printf '%s  # Caddy site config\n' "/etc/caddy/conf.d/${SERVICE_NAME}.caddy"
    fi
  } >"$PATHS_FILE"

  if id -u "$INSTALL_OWNER" >/dev/null 2>&1; then
    chown "$INSTALL_OWNER:$INSTALL_OWNER" "$PATHS_FILE" || true
  fi
}

report_secret_follow_up() {
  local missing=()

  if [[ -z "${API_KEY:-}" ]]; then
    missing+=("WIFI_PDF_API_KEY")
  fi

  if [[ "$ENABLE_WORKDRIVE" == "true" ]]; then
    [[ -z "${ZOHO_WORKDRIVE_CLIENT_ID:-}" ]] && missing+=("ZOHO_WORKDRIVE_CLIENT_ID")
    [[ -z "${ZOHO_WORKDRIVE_CLIENT_SECRET:-}" ]] && missing+=("ZOHO_WORKDRIVE_CLIENT_SECRET")
    [[ -z "${ZOHO_WORKDRIVE_REFRESH_TOKEN:-}" ]] && missing+=("ZOHO_WORKDRIVE_REFRESH_TOKEN")
  fi

  if [[ "${#missing[@]}" -gt 0 ]]; then
    log "Open ${ENV_FILE} and fill in these values:"
    for key in "${missing[@]}"; do
      log "  - ${key}"
    done
    log "Then restart the service:"
    log "  sudo systemctl restart ${SERVICE_NAME}"
  else
    log "Secrets file is populated: ${ENV_FILE}"
  fi
}

write_service_file() {
  local service_file="/etc/systemd/system/${SERVICE_NAME}.service"
  cat >"$service_file" <<EOF
[Unit]
Description=Password PDF Generator API
After=network.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${ENV_FILE}
Environment=WIFI_PDF_CONFIG_PATH=${CONFIG_PATH}
Environment=PATH=${INSTALL_DIR}/.venv/bin
ExecStart=${INSTALL_DIR}/.venv/bin/uvicorn wifi_pdf.api:app --host 127.0.0.1 --port ${PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable --now "$SERVICE_NAME"
}

configure_caddy() {
  if [[ -z "$HOST" ]]; then
    log "No hostname provided. Skipping Caddy configuration."
    return
  fi

  mkdir -p /etc/caddy/conf.d
  if [[ ! -f /etc/caddy/Caddyfile ]] || grep -Fq '/usr/share/caddy' /etc/caddy/Caddyfile; then
    cat >/etc/caddy/Caddyfile <<'EOF'
import /etc/caddy/conf.d/*.caddy
EOF
  elif ! grep -Fq 'import /etc/caddy/conf.d/*.caddy' /etc/caddy/Caddyfile; then
    printf '\nimport /etc/caddy/conf.d/*.caddy\n' >> /etc/caddy/Caddyfile
  fi

  cat >"/etc/caddy/conf.d/${SERVICE_NAME}.caddy" <<EOF
${HOST} {
    reverse_proxy 127.0.0.1:${PORT}
}
EOF

  caddy fmt --overwrite /etc/caddy/Caddyfile >/dev/null
  caddy fmt --overwrite "/etc/caddy/conf.d/${SERVICE_NAME}.caddy" >/dev/null
  caddy validate --config /etc/caddy/Caddyfile
  systemctl enable --now caddy
  systemctl reload caddy
}

configure_ufw() {
  if [[ "$UFW_MODE" == "false" ]]; then
    log "Skipping UFW configuration."
    return
  fi

  ufw allow OpenSSH >/dev/null 2>&1 || true
  if [[ -n "$HOST" ]]; then
    ufw allow 80/tcp >/dev/null 2>&1 || true
    ufw allow 443/tcp >/dev/null 2>&1 || true
  fi
  ufw --force enable >/dev/null 2>&1 || true
}

main() {
  require_root
  initialize_context

  prompt HOST "Public hostname for Caddy/HTTPS (leave blank to skip Caddy)" false "$HOST"
  prompt API_KEY "Webhook API key" true "$(generate_secret)"
  prompt_yes_no ENABLE_WORKDRIVE "Enable Zoho WorkDrive upload" false
  prompt ZOHO_REGION "Zoho region (com, eu, in, com.au)" false "$ZOHO_REGION"

  if [[ "$ENABLE_WORKDRIVE" == "true" ]]; then
    prompt ZOHO_WORKDRIVE_CLIENT_ID "Zoho WorkDrive client id"
    prompt ZOHO_WORKDRIVE_CLIENT_SECRET "Zoho WorkDrive client secret" true
    prompt ZOHO_WORKDRIVE_REFRESH_TOKEN "Zoho WorkDrive refresh token" true
    prompt ZOHO_WORKDRIVE_PARENT_FOLDER_ID "Default WorkDrive folder id (optional)"
  fi

  ensure_packages
  ensure_user_and_dirs
  sync_repo
  install_python_deps
  configure_runtime_json
  write_env_file
  write_install_metadata
  write_service_file
  configure_caddy
  configure_ufw
  write_paths_file

  log "Install complete."
  log "Code directory: ${INSTALL_DIR}"
  log "Runtime config: ${CONFIG_PATH}"
  log "Secrets file: ${ENV_FILE}"
  log "Service: ${SERVICE_NAME}"
  log "Path inventory: ${PATHS_FILE}"
  report_secret_follow_up
  if [[ -n "$HOST" ]]; then
    log "Public health check: https://${HOST}/health"
  else
    log "Local health check: curl http://127.0.0.1:${PORT}/health"
  fi
}

main "$@"
