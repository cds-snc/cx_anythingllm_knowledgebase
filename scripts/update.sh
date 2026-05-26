#!/usr/bin/env bash
# update.sh — Download the latest knowledge base snapshot and restart
# Usage: bash scripts/update.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err()  { printf "${RED}[✗]${NC} %s\n" "$*"; exit 1; }

echo ""
echo "=== CX Knowledge Base — Update ==="
echo ""

# ── Find docker-compose command ────────────────────────────────────────────────
if docker compose version &>/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose &>/dev/null; then
  DC="docker-compose"
else
  err "Could not find docker compose. Is Docker Desktop installed and running?"
fi

# ── Auto-detect Colima socket ──────────────────────────────────────────────────
if [ -z "${DOCKER_HOST:-}" ]; then
  for sock in "$HOME/.colima/default/docker.sock" "$HOME/.colima/docker.sock"; do
    if [ -S "$sock" ]; then
      export DOCKER_HOST="unix://$sock"
      warn "Detected Colima — using $DOCKER_HOST"
      break
    fi
  done
fi

# ── Check Docker is running ────────────────────────────────────────────────────
if ! docker info &>/dev/null 2>&1; then
  err "Docker is not running. Open Docker Desktop and wait for it to start."
fi

# ── Fetch latest release info ──────────────────────────────────────────────────
echo "Checking for latest snapshot..."
RELEASE_JSON=$(curl -sf \
  "https://api.github.com/repos/cds-snc/cx_anythingllm_knowledgebase/releases/latest" \
  || true)

if [ -z "${RELEASE_JSON:-}" ]; then
  err "Could not reach GitHub. Check your internet connection."
fi

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

if [ -z "${LATEST_URL:-}" ] || [ "$LATEST_URL" = " " ]; then
  err "No storage snapshot found in the latest release.
  Check: https://github.com/cds-snc/cx_anythingllm_knowledgebase/releases"
fi

# ── Check if already up to date ───────────────────────────────────────────────
CURRENT_TAG=""
[ -f "storage/.release-tag" ] && CURRENT_TAG=$(cat storage/.release-tag)

if [ "$CURRENT_TAG" = "$LATEST_TAG" ]; then
  ok "Already on latest ($LATEST_TAG). Nothing to do."
  exit 0
fi

echo "Updating: '${CURRENT_TAG:-none}' → $LATEST_TAG"
echo ""

# ── Stop container ─────────────────────────────────────────────────────────────
echo "Stopping AnythingLLM..."
$DC down 2>/dev/null || true

# ── Backup existing storage ────────────────────────────────────────────────────
if [ -d "storage" ] && [ "$(ls -A storage 2>/dev/null)" ]; then
  BACKUP="storage-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
  echo "Backing up current storage to $BACKUP..."
  tar -czf "$BACKUP" storage/
fi

# ── Download and extract new snapshot ─────────────────────────────────────────
echo "Downloading $LATEST_TAG..."
curl -L --progress-bar -o /tmp/storage-new.tar.gz "$LATEST_URL"

echo "Extracting..."
rm -rf storage/
tar -xzf /tmp/storage-new.tar.gz
rm /tmp/storage-new.tar.gz

echo "$LATEST_TAG" > storage/.release-tag

# ── Restart ────────────────────────────────────────────────────────────────────
echo "Starting AnythingLLM with updated knowledge base..."
$DC up -d

echo ""
printf "Waiting for AnythingLLM to be ready"
for i in $(seq 1 30); do
  if curl -s http://localhost:3001/api/ping 2>/dev/null | grep -q '"online":true'; then
    break
  fi
  printf "."
  sleep 2
done
echo ""

if curl -s http://localhost:3001/api/ping 2>/dev/null | grep -q '"online":true'; then
  echo ""
  ok "Updated to $LATEST_TAG"
  echo "  AnythingLLM running at: http://localhost:3001"
  echo ""
else
  err "AnythingLLM failed to start after update.
  Check: $DC logs --tail 30"
fi
