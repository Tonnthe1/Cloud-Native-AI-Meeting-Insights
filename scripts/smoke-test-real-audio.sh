#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  printf 'Usage: %s <audio-file> [frontend-base-url]\n' "$0" >&2
  exit 2
fi

AUDIO_FILE=$1
FRONTEND_BASE_URL=${2:-http://localhost:3000}
TIMEOUT_SECONDS=${SMOKE_TIMEOUT_SECONDS:-1800}

if [[ ! -f "${AUDIO_FILE}" ]]; then
  printf 'Audio file does not exist: %s\n' "${AUDIO_FILE}" >&2
  exit 1
fi

for command in curl python3; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "${command}" >&2
    exit 1
  fi
done

FRONTEND_BASE_URL=${FRONTEND_BASE_URL%/}
log() {
  printf '[real-audio-smoke] %s\n' "$*"
}

log "Uploading through ${FRONTEND_BASE_URL}/api/analyze-meeting"
upload_json=$(curl --fail-with-body --silent --show-error \
  --form "file=@${AUDIO_FILE}" \
  "${FRONTEND_BASE_URL}/api/analyze-meeting")
meeting_id=$(python3 -c \
  'import json,sys; print(json.loads(sys.argv[1])["meeting_id"])' \
  "${upload_json}")

log "Meeting ${meeting_id} was accepted; polling every 3 seconds."
started_at=$(date +%s)
while true; do
  meeting_json=$(curl --fail-with-body --silent --show-error \
    "${FRONTEND_BASE_URL}/api/meetings/${meeting_id}")
  meeting_status=$(python3 -c \
    'import json,sys; print(json.loads(sys.argv[1]).get("status") or "unknown")' \
    "${meeting_json}")
  log "Meeting ${meeting_id} status: ${meeting_status}"

  case "${meeting_status}" in
    completed)
      transcript_length=$(python3 -c \
        'import json,sys; print(len((json.loads(sys.argv[1]).get("transcript") or "").strip()))' \
        "${meeting_json}")
      if [[ "${transcript_length}" -eq 0 ]]; then
        printf 'Meeting completed without a transcript.\n' >&2
        exit 1
      fi
      log "Completed with a persisted transcript (${transcript_length} characters)."
      exit 0
      ;;
    failed)
      printf 'Meeting processing failed: %s\n' "${meeting_json}" >&2
      exit 1
      ;;
  esac

  if (( $(date +%s) - started_at >= TIMEOUT_SECONDS )); then
    printf 'Timed out after %s seconds waiting for meeting %s.\n' \
      "${TIMEOUT_SECONDS}" "${meeting_id}" >&2
    exit 1
  fi
  sleep 3
done
