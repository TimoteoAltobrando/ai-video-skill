#!/bin/sh
# Generate one image with Codex CLI (its image_gen tool) from a prompt stored in a file.
#
#   sh codex_image.sh <folder> <name> [reference.png]
#
# Reads <folder>/prompt-<name>.md and expects Codex to save <folder>/<name>.png (the prompt must ask for it: see
# assets/templates/image-prompt.md). With [reference.png] Codex also sees that image and keeps its style. Codex's
# report goes to <folder>/log/. About 1-2 minutes per image; several can run in parallel.
# Model: the CODEX_MODEL environment variable; if it is empty, Codex decides. Some setups need a specific model for
# image generation: try a simple image first and write down the model that works.
set -e
D="$(cd "$1" && pwd)"
N="$2"
REF="$3"
mkdir -p "$D/log"
[ -f "$D/prompt-$N.md" ] || { echo "missing $D/prompt-$N.md"; exit 1; }
set -- exec --skip-git-repo-check -s workspace-write -C "$D"
[ -n "$CODEX_MODEL" ] && set -- "$@" -m "$CODEX_MODEL"
[ -n "$REF" ] && set -- "$@" -i "$(cd "$(dirname "$REF")" && pwd)/$(basename "$REF")"
codex "$@" -o "$D/log/last-$N.txt" - < "$D/prompt-$N.md" > "$D/log/codex-$N.log" 2>&1 || true
if [ -f "$D/$N.png" ]; then echo "ok $D/$N.png"; else echo "MISSING $N.png: read $D/log/codex-$N.log"; exit 1; fi
