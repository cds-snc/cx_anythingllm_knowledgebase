#!/usr/bin/env bash
# setup.sh — One-time Codespace setup (runs on first creation only).
# Generates .env with real secrets, injects Azure creds from Codespaces
# secrets, and downloads the pre-embedded knowledge base.
set -euo pipefail

echo "=== CX Knowledge Base — Codespace Setup ==="

# ── Generate .env with real secrets ──────────────────────────────────────────
cp .env.example .env

sed -i "s|^SIG_KEY=.*|SIG_KEY='$(openssl rand -hex 32)'|"       .env
sed -i "s|^SIG_SALT=.*|SIG_SALT='$(openssl rand -hex 32)'|"     .env
sed -i "s|^JWT_SECRET=.*|JWT_SECRET='$(openssl rand -hex 32)'|"  .env

# Inject Azure credentials from Codespaces secrets (if set)
if [ -n "${AZURE_OPENAI_KEY:-}" ]; then
  sed -i "s|^AZURE_OPENAI_KEY=.*|AZURE_OPENAI_KEY=${AZURE_OPENAI_KEY}|" .env
  echo "[setup] Azure OpenAI key injected from Codespaces secrets"
else
  echo "[setup] WARNING: AZURE_OPENAI_KEY not set — chat will not work until configured"
fi
if [ -n "${AZURE_OPENAI_ENDPOINT:-}" ]; then
  sed -i "s|^AZURE_OPENAI_ENDPOINT=.*|AZURE_OPENAI_ENDPOINT='${AZURE_OPENAI_ENDPOINT}'|" .env
  echo "[setup] Azure OpenAI endpoint injected from Codespaces secrets"
fi

echo "[setup] .env generated with fresh secrets"

# ── Download knowledge base snapshot ─────────────────────────────────────────
echo "[setup] Downloading knowledge base..."
RELEASE_URL=$(curl -sf \
  "https://api.github.com/repos/cds-snc/cx_anythingllm_knowledgebase/releases/latest" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for a in data.get('assets', []):
    if a['name'].startswith('storage') and a['name'].endswith('.tar.gz'):
        print(a['browser_download_url'])
        break
" 2>/dev/null || true)

if [ -n "${RELEASE_URL:-}" ]; then
  curl -L --progress-bar -o /tmp/storage.tar.gz "$RELEASE_URL"
  tar -xzf /tmp/storage.tar.gz
  rm -f /tmp/storage.tar.gz
  echo "[setup] Knowledge base loaded"
else
  echo "[setup] WARNING: Could not download knowledge base — embed documents manually in the UI"
  mkdir -p storage
fi

echo "[setup] Done — AnythingLLM will start automatically"
