#!/usr/bin/env bash
# update.sh — Download the latest knowledge base snapshot and restart
# Usage: ./scripts/update.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== CX AnythingLLM — Update Knowledge Base ==="
echo ""

# --- Check Docker daemon ---
if ! docker info &>/dev/null; then
  echo "ERROR: Docker daemon not running. Start Colima or Docker Desktop first."
  exit 1
fi

# --- Fetch latest release ---
echo "Checking for latest snapshot on GitHub Releases..."
LATEST=$(curl -s https://api.github.com/repos/cds-snc/cx_anythingllm_knowledgebase/releases/latest \
  -H "Accept: application/vnd.github.v3+json")

LATEST_TAG=$(echo "$LATEST" | grep '"tag_name"' | head -1 | cut -d'"' -f4)
LATEST_URL=$(echo "$LATEST" | grep '"browser_download_url"' | grep 'storage\.tar\.gz' | head -1 | cut -d'"' -f4)

if [ -z "$LATEST_URL" ]; then
  echo "ERROR: No storage snapshot found in GitHub Releases."
  echo "Has the corpus been embedded and released? Check:"
  echo "  https://github.com/cds-snc/cx_anythingllm_knowledgebase/releases"
  exit 1
fi

echo "Latest release: $LATEST_TAG"

# --- Check current version ---
CURRENT_TAG=""
if [ -f "storage/.release-tag" ]; then
  CURRENT_TAG=$(cat storage/.release-tag)
fi

if [ "$CURRENT_TAG" = "$LATEST_TAG" ]; then
  echo "[✓] Already on latest release ($LATEST_TAG). Nothing to do."
  exit 0
fi

echo "Updating from '${CURRENT_TAG:-none}' → $LATEST_TAG"
echo ""

# --- Stop container ---
echo "Stopping AnythingLLM..."
docker-compose down 2>/dev/null || true

# --- Backup existing storage ---
if [ -d "storage" ] && [ "$(ls -A storage 2>/dev/null)" ]; then
  BACKUP="storage-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
  echo "Backing up current storage to $BACKUP..."
  tar -czf "$BACKUP" storage/
fi

# --- Download new snapshot ---
echo "Downloading $LATEST_TAG..."
curl -L -o /tmp/storage-new.tar.gz "$LATEST_URL"

echo "Extracting..."
# Replace storage directory (keep .env outside storage, so safe to wipe)
rm -rf storage/
tar -xzf /tmp/storage-new.tar.gz
rm /tmp/storage-new.tar.gz

# --- Write version tag ---
echo "$LATEST_TAG" > storage/.release-tag

# --- Restart container ---
echo "Starting AnythingLLM with updated knowledge base..."
docker-compose up -d

echo ""
echo "Waiting for AnythingLLM to start..."
for i in {1..30}; do
  if curl -s http://localhost:3001/api/ping 2>/dev/null | grep -q '"online":true'; then
    break
  fi
  sleep 2
done

if curl -s http://localhost:3001/api/ping 2>/dev/null | grep -q '"online":true'; then
  echo ""
  echo "[✓] Updated to $LATEST_TAG"
  echo "    AnythingLLM running at: http://localhost:3001"
else
  echo "ERROR: AnythingLLM failed to start after update."
  echo "Check: docker-compose logs -f anythingllm"
  exit 1
fi
