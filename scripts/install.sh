#!/usr/bin/env bash
# install.sh — One-time setup for a new teammate
# Usage: bash scripts/install.sh

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

check_cmd "docker"         "Install Docker Desktop: https://docs.docker.com/get-docker/"
check_cmd "docker-compose" "Install docker-compose: brew install docker-compose"
check_cmd "curl"           "Install curl"
check_cmd "gh"             "Install GitHub CLI: brew install gh  —  then run: gh auth login"

echo "[✓] Prerequisites found"

# --- Check Docker daemon ---
if ! docker info &>/dev/null; then
  echo ""
  echo "ERROR: Docker daemon is not running."
  echo "  On Docker Desktop: start Docker Desktop from your Applications folder."
  echo "  On macOS with Colima: run 'colima start' then re-run this script."
  echo ""
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
  echo "ACTION REQUIRED: Open .env in a text editor and fill in your credentials:"
  echo "  AZURE_OPENAI_KEY=<your Azure OpenAI API key>"
  echo "  AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/"
  echo ""
  echo "Then re-run this script."
  echo ""
  exit 0
fi

# --- Verify Azure key is set ---
if grep -q 'AZURE_OPENAI_KEY=your-azure-openai-api-key-here' .env 2>/dev/null; then
  echo ""
  echo "ERROR: AZURE_OPENAI_KEY is not set in .env"
  echo "Edit .env and fill in your Azure OpenAI API key, then re-run."
  exit 1
fi
if ! grep -q '^AZURE_OPENAI_KEY=.' .env 2>/dev/null; then
  echo ""
  echo "ERROR: AZURE_OPENAI_KEY is missing from .env"
  echo "Edit .env and add: AZURE_OPENAI_KEY=<your key>"
  exit 1
fi
echo "[✓] .env configured"

# --- Download latest storage snapshot ---
echo ""
echo "Checking for latest knowledge base snapshot..."
SNAPSHOT_DIR="/tmp/anyllm_snapshot_$$"
mkdir -p "$SNAPSHOT_DIR"

if gh release download --repo cds-snc/cx_anythingllm_knowledgebase \
     --pattern 'storage*.tar.gz' --dir "$SNAPSHOT_DIR" 2>/dev/null; then
  TARBALL=$(ls "$SNAPSHOT_DIR"/storage*.tar.gz 2>/dev/null | head -1)
  if [ -n "$TARBALL" ]; then
    echo "Extracting knowledge base..."
    tar -xzf "$TARBALL"
    rm -rf "$SNAPSHOT_DIR"
    echo "[✓] Knowledge base loaded (21 documents pre-embedded)"
  fi
else
  rm -rf "$SNAPSHOT_DIR"
  echo "[!] Could not download snapshot — starting with empty storage."
  echo "    Make sure you are logged in to GitHub CLI: gh auth login"
  mkdir -p storage
fi

# --- Stop any previous instance on this port ---
echo ""
echo "Stopping any previous instance..."
docker-compose down 2>/dev/null || true

# --- Pull latest image and start ---
echo "Pulling AnythingLLM image..."
docker-compose pull

echo "Starting AnythingLLM..."
docker-compose up -d

echo ""
echo "Waiting for AnythingLLM to start (this can take up to 60 seconds)..."
for i in $(seq 1 30); do
  if curl -s http://localhost:3001/api/ping 2>/dev/null | grep -q '"online":true'; then
    break
  fi
  sleep 2
done

if curl -s http://localhost:3001/api/ping 2>/dev/null | grep -q '"online":true'; then
  echo ""
  echo "=== Install complete! ==="
  echo ""
  echo "Open your browser and go to: http://localhost:3001"
  echo ""
  echo "  - Create an account when prompted (local to your machine)"
  echo "  - Select the CX Knowledge Base workspace"
  echo "  - Type your question and press Enter"
  echo ""
  echo "To stop: docker-compose down"
  echo "To update corpus: bash scripts/update.sh"
else
  echo ""
  echo "ERROR: AnythingLLM did not start in time."
  echo "Check what went wrong with: docker-compose logs anythingllm"
  exit 1
fi
