#!/usr/bin/env bash

set -euo pipefail

REPOSITORY_URL=${MEETING_INSIGHTS_REPOSITORY_URL:-https://github.com/Tonnthe1/Cloud-Native-AI-Meeting-Insights.git}
INSTALL_DIR=${MEETING_INSIGHTS_INSTALL_DIR:-${HOME}/meeting-insights}
REF=${MEETING_INSIGHTS_REF:-main}
MEETING_INSIGHTS_PREBUILT=${MEETING_INSIGHTS_PREBUILT:-true}
export MEETING_INSIGHTS_PREBUILT

log() {
  printf '[meeting-insights-installer] %s\n' "$*"
}

fail() {
  printf '[meeting-insights-installer] ERROR: %s\n' "$*" >&2
  exit 1
}

command -v git >/dev/null 2>&1 || fail "git is required."
command -v docker >/dev/null 2>&1 || fail "Docker is required: https://docs.docker.com/get-docker/"
docker info >/dev/null 2>&1 || fail "Docker is installed but the daemon is not running."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."

if [[ -e "${INSTALL_DIR}" && ! -d "${INSTALL_DIR}/.git" ]]; then
  fail "${INSTALL_DIR} already exists and is not a Git repository. Set MEETING_INSIGHTS_INSTALL_DIR to another directory."
fi

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  log "Cloning Meeting Insights into ${INSTALL_DIR}."
  git clone --branch "${REF}" --depth 1 "${REPOSITORY_URL}" "${INSTALL_DIR}"
else
  log "Using existing checkout at ${INSTALL_DIR}."
  if [[ -z "$(git -C "${INSTALL_DIR}" status --porcelain)" ]]; then
    git -C "${INSTALL_DIR}" fetch --depth 1 origin "${REF}"
    git -C "${INSTALL_DIR}" checkout --quiet --detach FETCH_HEAD
  else
    log "Checkout has local changes; leaving them untouched."
  fi
fi

cd "${INSTALL_DIR}"
exec bash scripts/quickstart.sh up
