#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${PASSWORD_PDF_SERVICE_NAME:-password-pdf-generator}"
INSTALL_DIR="${PASSWORD_PDF_INSTALL_DIR:-/opt/password-pdf-generator}"
REPO_REF="${PASSWORD_PDF_REPO_REF:-main}"

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

systemctl restart "${SERVICE_NAME}"
systemctl status "${SERVICE_NAME}" --no-pager

