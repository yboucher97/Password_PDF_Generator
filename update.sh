#!/usr/bin/env bash
set -euo pipefail

DEFAULT_SERVICE_ROOT="${PASSWORD_PDF_SERVICE_ROOT:-/opt/services/password-pdf-generator}"
DEFAULT_CONFIG_DIR="${PASSWORD_PDF_CONFIG_DIR:-${DEFAULT_SERVICE_ROOT}/config}"
META_FILE="${PASSWORD_PDF_META_FILE:-${DEFAULT_CONFIG_DIR}/install-meta.env}"

if [[ ! -f "$META_FILE" ]]; then
  echo "Install metadata not found: ${META_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$META_FILE"
if [[ -f "${ENV_FILE:-}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi
set +a

APP_DIR="${PASSWORD_PDF_APP_DIR:-${APP_DIR:-${DEFAULT_SERVICE_ROOT}/app}}"
REPO_REF="${PASSWORD_PDF_REPO_REF:-${REPO_REF:-main}}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo ${APP_DIR}/update.sh" >&2
  exit 1
fi

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "Install directory is not a git checkout: ${APP_DIR}" >&2
  exit 1
fi

git config --global --add safe.directory "${APP_DIR}"
git -C "${APP_DIR}" fetch --prune origin
git -C "${APP_DIR}" checkout "${REPO_REF}"
git -C "${APP_DIR}" reset --hard "origin/${REPO_REF}"

exec bash "${APP_DIR}/install.sh"
