#!/usr/bin/env bash
# install.sh — One-time setup for a new teammate
# Usage: ./scripts/install.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== CX AnythingLLM Knowledge Base — Install ==="
echo ""

# --- Check prerequisites ---
check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    echo "ERROR: '$1' not found. $2"
    exit 1
  fi
}

check_cmd "docker" "Install Docker Desktop (Mac/Win) or Colima (Mac): brew install colima docker docker-compose"
check_cmd "docker-compose" "Install docker-compose: brew install docker-compose"
check_cmd "curl" "Install curl"

echo "[✓] Prerequisites found"

# --- Check Docker daemon ---
if ! docker info &>/dev/null; then
  echo ""
  echo "Docker daemon is not running. On macOS with Colima, run:"
  echo "  colima start --arch aarch64 --memory 4 --cpu 2"
  echo "  export DOCKER_HOST=\"unix://\$HOME/.colima/docker.sock\""
  echo ""
  echo "On Docker Desktop, just start Docker Desktop."
  exit 1
fi
echo "[✓] Docker daemon running"

# --- Create .env from example ---
if [ ! -f ".env" ]; then
  if [ ! -f ".env.example" ]; then
    echo "ERROR: .env.example not found"
    exit 1
  fi
  cp .env.example .env
  echo ""
  echo "Created .env from .env.example"
  echo ""
  echo "ACTION REQUIRED: Edit .env and fill in your OPEN_AI_KEY."
  echo "  Get a key at: https://platform.openai.com/api-keys"
  echo "  Then re-run this script."
  echo ""
  exit 0
fi

# --- Verify OpenAI key is set ---
if grep -q "OPEN_AI_KEY=$" .env || grep -q "OPEN_AI_KEY=your-key-here" .env 2>/dev/null; then
  echo "ERROR: OPEN_AI_KEY is not set in .env"
  echo "Edit .env and add your OpenAI API key, then re-run."
  exit 1
fi
echo "[✓] .env configured"

# --- Download latest storage snapshot ---
echo ""
echo "Checking for latest knowledge base snapshot..."
LATEST_URL=$(curl -s https://api.github.com/repos/cds-snc/cx_anythingllm_knowledgebase/releases/latest \
  -H "Accept: application/vnd.github.v3+json" \
  | grep '"browser_download_url"' \
  | grep 'storage\.tar\.gz' \
  | head -1 \
  | cut -d'"' -f4)

if [ -n "$LATEST_URL" ]; then
  echo "Downloading knowledge base: $LATEST_URL"
  curl -L -o /tmp/storage.tar.gz "$LATEST_URL"
  echo "Extracting..."
  tar -xzf /tmp/storage.tar.gz
  rm /tmp/storage.tar.gz
  echo "[✓] Knowledge base loaded"
else
  echo "[!] No snapshot found in GitHub Releases — starting with empty storage."
  mkdir -p storage
fi

# --- Pull latest image and start ---
echo ""
echo "Pulling AnythingLLM image..."
docker-compose pull

echo "Starting AnythingLLM..."
docker-compose up -d

echo ""
echo "Waiting for AnythingLLM to start..."
for i in {1..30}; do
  if curl -s http://localhost:3001/api/ping | grep -q '"online":true'; then
    break
  fi
  sleep 2
done

if curl -s http://localhost:3001/api/ping | grep -q '"online":true'; then
  echo ""
  echo "=== Install complete! ==="
  echo ""
  echo "AnythingLLM is running at: http://localhost:3001"
  echo ""
  echo "First-time setup (run once):"
  echo "  1. Open http://localhost:3001"
  echo "  2. Complete the onboarding wizard"
  echo "  3. Create a workspace named 'Research'"
  echo "  4. Set Chat Mode → Query (prevents hallucination)"
  echo "  5. Set system prompt (see README)"
  echo ""
  echo "To stop: docker-compose down"
  echo "To update to latest corpus: ./scripts/update.sh"
else
  echo "ERROR: AnythingLLM did not start. Check logs:"
  echo "  docker-compose logs -f anythingllm"
  exit 1
fi
