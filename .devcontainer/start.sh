#!/usr/bin/env bash
# start.sh — Runs on every Codespace start.
# Checks for a newer knowledge base release, updates if needed, then starts AnythingLLM.
set -euo pipefail

CURRENT_TAG=""
[ -f "storage/.release-tag" ] && CURRENT_TAG=$(cat storage/.release-tag)

LATEST_TAG=""
LATEST_URL=""
RELEASE_JSON=$(curl -sf \
  "https://api.github.com/repos/cds-snc/cx_anythingllm_knowledgebase/releases/latest" \
  2>/dev/null || true)

if [ -n "${RELEASE_JSON:-}" ]; then
  read -r LATEST_TAG LATEST_URL < <(echo "$RELEASE_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tag = data.get('tag_name', '')
url = ''
for a in data.get('assets', []):
    if a['name'].startswith('storage') and a['name'].endswith('.tar.gz'):
        url = a['browser_download_url']
        break
print(tag, url)
" 2>/dev/null || echo " ")
fi

if [ -n "${LATEST_TAG:-}" ] && [ "$LATEST_TAG" != "$CURRENT_TAG" ] && [ -n "${LATEST_URL:-}" ]; then
  echo "[start] Updating knowledge base: '${CURRENT_TAG:-none}' → ${LATEST_TAG}"
  curl -L --progress-bar -o /tmp/storage.tar.gz "$LATEST_URL"
  rm -rf storage
  tar -xzf /tmp/storage.tar.gz
  rm -f /tmp/storage.tar.gz
  echo "[start] Updated to ${LATEST_TAG}"
else
  echo "[start] Knowledge base is current (${CURRENT_TAG:-none})"
fi

docker compose up -d
timeout 120 bash -c 'until curl -sf http://localhost:3001/api/ping >/dev/null 2>&1; do sleep 2; done' \
  && echo "[start] AnythingLLM is ready at port 3001" \
  || echo "[start] WARNING: AnythingLLM did not become healthy in time"
