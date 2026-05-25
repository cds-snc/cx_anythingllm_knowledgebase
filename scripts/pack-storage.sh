#!/usr/bin/env bash
# pack-storage.sh — Package the current storage directory for a release
# Run this after embedding is complete on the maintainer machine.
# Usage: ./scripts/pack-storage.sh [version-tag]
# Example: ./scripts/pack-storage.sh v2026-05-25

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TAG="${1:-v$(date +%Y-%m-%d)}"
OUTPUT="storage-${TAG}.tar.gz"

if [ ! -d "storage" ]; then
  echo "ERROR: storage/ directory not found. Run the container and embed documents first."
  exit 1
fi

echo "Packaging storage/ as $OUTPUT..."
echo "Tag: $TAG"

# Write version tag into the snapshot
echo "$TAG" > storage/.release-tag

# Exclude chat history, log files, and any temp files
# Keep: anythingllm.db (workspaces/settings), documents/, vector-cache/
tar -czf "$OUTPUT" \
  --exclude="storage/logs" \
  --exclude="storage/*.log" \
  --exclude="storage/tmp" \
  storage/

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "[✓] Created $OUTPUT ($SIZE)"
echo ""
echo "To create a GitHub release:"
echo "  gh release create $TAG $OUTPUT \\"
echo "    --title 'Knowledge Base $TAG' \\"
echo "    --notes 'Embedded corpus snapshot. Run ./scripts/update.sh to apply.' \\"
echo "    --repo cds-snc/cx_anythingllm_knowledgebase"
