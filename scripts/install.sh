#!/usr/bin/env bash
# install.sh — One-time setup for a new teammate
# Usage: bash scripts/install.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "${GREEN}[✓]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[!]${NC} %s\n" "$*"; }
err()  { printf "${RED}[✗]${NC} %s\n" "$*"; exit 1; }

echo ""
echo "=== CX Knowledge Base — Setup ==="
echo ""

# ── Step 1: Find the right docker-compose command ────────────────────────────
if docker compose version &>/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose &>/dev/null; then
  DC="docker-compose"
else
  err "Could not find docker compose.
  → Make sure Docker Desktop is installed and running.
  → Download it at: https://www.docker.com/products/docker-desktop/"
fi

# ── Step 2: Auto-detect Colima socket (most users won't need this) ────────────
if [ -z "${DOCKER_HOST:-}" ]; then
  for sock in "$HOME/.colima/default/docker.sock" "$HOME/.colima/docker.sock"; do
    if [ -S "$sock" ]; then
      export DOCKER_HOST="unix://$sock"
      warn "Detected Colima — using $DOCKER_HOST"
      break
    fi
  done
fi

# ── Step 3: Check Docker is actually running ──────────────────────────────────
if ! docker info &>/dev/null 2>&1; then
  err "Docker is not running.
  → Open Docker Desktop from your Applications folder and wait for the whale
    icon to stop animating in the menu bar, then run this script again."
fi
ok "Docker is running"

# ── Step 4: Set up credentials ────────────────────────────────────────────────
needs_env_setup=false
if [ ! -f ".env" ]; then
  cp .env.example .env
  needs_env_setup=true
elif grep -q 'AZURE_OPENAI_KEY=your-azure-openai-api-key-here' .env 2>/dev/null; then
  needs_env_setup=true
fi

if [ "$needs_env_setup" = true ]; then
  echo ""
  echo "─── Azure OpenAI credentials ─────────────────────────────────────────────────"
  echo "You need two values from your team lead before continuing."
  echo ""

  read -r -p "  1. Azure OpenAI API key: " AZURE_KEY
  [ -z "$AZURE_KEY" ] && err "API key is required."

  read -r -p "  2. Azure endpoint URL (e.g. https://cds-platform-ai.openai.azure.com/): " AZURE_ENDPOINT
  [ -z "$AZURE_ENDPOINT" ] && err "Endpoint URL is required."

  # Auto-generate secrets so users don't have to
  SIG_KEY=$(openssl rand -hex 32)
  SIG_SALT=$(openssl rand -hex 32)
  JWT_SECRET=$(openssl rand -hex 32)

  # Write values into .env safely via Python (handles special chars in values)
  AZURE_KEY="$AZURE_KEY" AZURE_ENDPOINT="$AZURE_ENDPOINT" \
  SIG_KEY="$SIG_KEY" SIG_SALT="$SIG_SALT" JWT_SECRET="$JWT_SECRET" \
  python3 - <<'PYEOF'
import os
replacements = {
    'AZURE_OPENAI_KEY':    os.environ['AZURE_KEY'],
    'AZURE_OPENAI_ENDPOINT': "'" + os.environ['AZURE_ENDPOINT'].strip("'") + "'",
    'SIG_KEY':   "'" + os.environ['SIG_KEY']    + "'",
    'SIG_SALT':  "'" + os.environ['SIG_SALT']   + "'",
    'JWT_SECRET':"'" + os.environ['JWT_SECRET'] + "'",
}
with open('.env', 'r') as f:
    lines = f.readlines()
result = []
for line in lines:
    key = line.split('=')[0] if '=' in line else ''
    if key in replacements:
        result.append(f'{key}={replacements[key]}\n')
    else:
        result.append(line)
with open('.env', 'w') as f:
    f.writelines(result)
PYEOF

  echo ""
  ok "Credentials saved"
fi
ok ".env configured"

# ── Step 5: Download knowledge base snapshot ──────────────────────────────────
echo ""
echo "Downloading knowledge base (21 pre-embedded documents)..."
SNAPSHOT_DIR="/tmp/anyllm_snapshot_$$"
mkdir -p "$SNAPSHOT_DIR"

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
  curl -L --progress-bar -o "$SNAPSHOT_DIR/storage.tar.gz" "$RELEASE_URL"
  tar -xzf "$SNAPSHOT_DIR/storage.tar.gz"
  rm -rf "$SNAPSHOT_DIR"
  ok "Knowledge base loaded"
else
  rm -rf "$SNAPSHOT_DIR"
  warn "Could not download knowledge base — the assistant will start but you will"
  warn "need to embed documents manually in the UI."
  mkdir -p storage
fi

# ── Step 6: Start AnythingLLM ─────────────────────────────────────────────────
echo ""
echo "Stopping any previous instance..."
$DC down 2>/dev/null || true

echo "Downloading AnythingLLM image (first time: 2–5 minutes)..."
$DC pull

echo "Starting..."
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

  # ── Write the real API key to .env ─────────────────────────────────────────
  # AnythingLLM generates the key on first startup; retrieve it from the DB
  REAL_API_KEY=$(docker exec anythingllm node -e \
    "const {PrismaClient}=require('/app/server/node_modules/@prisma/client');
    const p=new PrismaClient();
    p.api_keys.findFirst().then(r=>{console.log(r ? r.secret : '');p.\$disconnect();})" \
    2>/dev/null || true)
  if [ -n "${REAL_API_KEY:-}" ]; then
    REAL_API_KEY="$REAL_API_KEY" python3 -c "
import os
key = os.environ['REAL_API_KEY']
with open('.env', 'r') as f: lines = f.readlines()
result = [f'ANYWHERE_API_KEY={key}\n' if l.startswith('ANYWHERE_API_KEY=') else l for l in lines]
with open('.env', 'w') as f: f.writelines(result)
"
    ok "API key saved to .env"
  fi

  echo ""
  echo "╔════════════════════════════════════════╗"
  echo "║        Setup complete!                 ║"
  echo "╚════════════════════════════════════════╝"
  echo ""
  echo "  Open your browser and go to:"
  echo "  → http://localhost:3001"
  echo ""
  echo "  Create an account when prompted (private to your Mac)."
  echo "  Select the CX Knowledge Base workspace."
  echo "  Type your question and press Enter."
  echo ""
  echo "  To stop:       $DC down"
  echo "  To start again: $DC up -d"
  echo ""
else
  err "AnythingLLM did not start in time.
  Check what went wrong with: $DC logs --tail 30"
fi
