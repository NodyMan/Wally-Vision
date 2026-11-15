#!/usr/bin/env bash
# Assemble the Space repository OUTSIDE OneDrive (avoids "file could not be read" errors) and commit it.
# Usage (from the hackathon folder):  bash deploy/huggingface/build_space.sh
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT=/c/skyblink_deploy/hf-space
if [ ! -d "$OUT/.git" ]; then
  git clone https://huggingface.co/spaces/bymakhmud/SkyBlink "$OUT"
fi
cd "$OUT"
rm -rf backend shared
mkdir -p backend shared
# tracked files only: no cache, FITS, database or .env
git -C "$ROOT" archive HEAD backend shared | tar -x -C "$OUT"
cp "$ROOT/deploy/huggingface/Dockerfile" "$ROOT/deploy/huggingface/README.md" .
git add -A
git commit -m "SkyBlink backend" || echo "nothing new to commit"
echo "Ready in $OUT. Push with:  cd $OUT && git push"
