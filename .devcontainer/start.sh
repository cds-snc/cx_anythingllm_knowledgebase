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

# ── Inject Azure credentials from Codespace secrets into .env ──────────────────
# These may not have been set during setup.sh if the Codespace secrets
# weren't available yet. Re-inject on every start to guarantee parity.
#
# IMPORTANT: AnythingLLM expects AZURE_OPENAI_ENDPOINT as the BASE resource URL
# only, e.g. https://myresource.openai.azure.com/
# It constructs the full /openai/deployments/... path internally.
# If someone pastes the full deployment URL from Azure Portal, strip it.
if [ -f .env ]; then
  if [ -n "${AZURE_OPENAI_KEY:-}" ]; then
    # Strip any surrounding quotes from the secret value
    CLEAN_KEY=$(echo "$AZURE_OPENAI_KEY" | sed "s/^['\"]//;s/['\"]$//")
    sed -i "s|^AZURE_OPENAI_KEY=.*|AZURE_OPENAI_KEY=${CLEAN_KEY}|" .env
    echo "[start] Azure OpenAI key injected from environment"
  fi
  if [ -n "${AZURE_OPENAI_ENDPOINT:-}" ]; then
    # Strip quotes, then strip everything after .azure.com/ to get the base URL
    CLEAN_ENDPOINT=$(echo "$AZURE_OPENAI_ENDPOINT" | sed "s/^['\"]//;s/['\"]$//" | sed 's|\(\.openai\.azure\.com\)/.*|\1/|')
    sed -i "s|^AZURE_OPENAI_ENDPOINT=.*|AZURE_OPENAI_ENDPOINT='${CLEAN_ENDPOINT}'|" .env
    echo "[start] Azure OpenAI endpoint set to: ${CLEAN_ENDPOINT}"
  fi
fi

docker compose up -d
timeout 120 bash -c 'until curl -sf http://localhost:3001/api/ping >/dev/null 2>&1; do sleep 2; done' \
  && echo "[start] AnythingLLM is ready at port 3001" \
  || { echo "[start] WARNING: AnythingLLM did not become healthy in time"; exit 1; }

# ── Enforce workspace config (parity with local) ──────────────────────────────
# Extract or create API key from the running container
API_KEY=$(docker exec anythingllm node -e "
  const { PrismaClient } = require('/app/server/node_modules/@prisma/client');
  const crypto = require('crypto');
  const p = new PrismaClient();
  (async () => {
    let key = await p.api_keys.findFirst();
    if (!key) {
      const secret = 'sk-' + crypto.randomBytes(16).toString('hex');
      key = await p.api_keys.create({ data: { secret } });
    }
    console.log(key.secret);
    await p.\$disconnect();
  })();
" 2>/dev/null || true)

if [ -n "${API_KEY:-}" ]; then
  echo "[start] Enforcing workspace settings..."
  curl -sf -X POST "http://localhost:3001/api/v1/workspace/cx-knowledge-base/update" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "chatMode": "query",
      "openAiTemp": 0,
      "topN": 10,
      "similarityThreshold": 0.25,
      "vectorSearchMode": "rerank",
      "openAiPrompt": "You are a knowledgeable assistant for BC native plant gardening. You ONLY answer questions using the context documents provided to you in each response. Do not use general knowledge, do not guess, and do not infer beyond what the documents explicitly state. Critically: if a document mentions a plant name but does not explicitly confirm the specific attribute being asked about (such as flower colour, height, or water requirements), do not describe that attribute — acknowledge the gap instead. If the documents do not contain enough information to answer the question, say so clearly. Never fabricate plant names, flower colours, statistics, percentages, dates, or rankings that are not stated in the documents.",
      "queryRefusalResponse": "I was not able to find relevant information about this in the documents available to me. I can only answer questions based on the native plant guides in my knowledge base."
    }' >/dev/null 2>&1 \
    && echo "[start] Workspace configured: query mode, reranker on, temp 0" \
    || echo "[start] WARNING: Could not enforce workspace settings — check manually in the UI"
else
  echo "[start] WARNING: Could not extract API key — workspace settings may need manual config"
fi
