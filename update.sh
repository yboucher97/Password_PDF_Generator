#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="${PASSWORD_PDF_CONFIG_DIR:-/etc/password-pdf-generator}"
META_FILE="${PASSWORD_PDF_META_FILE:-${CONFIG_DIR}/install-meta.env}"

if [[ -f "$META_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$META_FILE"
fi

SERVICE_NAME="${PASSWORD_PDF_SERVICE_NAME:-${SERVICE_NAME:-password-pdf-generator}}"
INSTALL_DIR="${PASSWORD_PDF_INSTALL_DIR:-${INSTALL_DIR:-/opt/password-pdf-generator}}"
DATA_DIR="${PASSWORD_PDF_DATA_DIR:-${DATA_DIR:-/var/lib/password-pdf-generator}}"
CONFIG_DIR="${PASSWORD_PDF_CONFIG_DIR:-${CONFIG_DIR:-/etc/password-pdf-generator}}"
CONFIG_PATH="${PASSWORD_PDF_CONFIG_PATH:-${CONFIG_PATH:-${CONFIG_DIR}/brand_settings.json}}"
ENV_FILE="${PASSWORD_PDF_ENV_FILE:-${ENV_FILE:-/etc/password-pdf-generator.env}}"
PATHS_FILE="${PASSWORD_PDF_PATHS_FILE:-${PATHS_FILE:-}}"
HOST="${PASSWORD_PDF_HOST:-${HOST:-}}"
REPO_REF="${PASSWORD_PDF_REPO_REF:-${REPO_REF:-main}}"
INSTALL_OWNER="${PASSWORD_PDF_INSTALL_OWNER:-${INSTALL_OWNER:-}}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ${INSTALL_DIR}/update.sh" >&2
  exit 1
fi

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  echo "Install directory is not a git checkout: ${INSTALL_DIR}" >&2
  exit 1
fi

git -C "${INSTALL_DIR}" fetch --prune origin
git -C "${INSTALL_DIR}" checkout "${REPO_REF}"
git -C "${INSTALL_DIR}" reset --hard "origin/${REPO_REF}"

python3 -m venv "${INSTALL_DIR}/.venv"
"${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

if [[ -n "$PATHS_FILE" ]]; then
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
  if [[ -n "$INSTALL_OWNER" ]] && id -u "$INSTALL_OWNER" >/dev/null 2>&1; then
    chown "$INSTALL_OWNER:$INSTALL_OWNER" "$PATHS_FILE" || true
  fi
fi

systemctl daemon-reload
systemctl restart "${SERVICE_NAME}"
systemctl status "${SERVICE_NAME}" --no-pager
