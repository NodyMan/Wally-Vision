#!/usr/bin/env bash
# Assemble the Space repository OUTSIDE OneDrive (avoids "file could not be read" errors) and commit it.
# Usage (from the hackathon folder):  bash deploy/huggingface/build_space.sh
# Hugging Face rejects binary files that are not in LFS/Xet, so the preset PNGs go through git-lfs.
# The Space repository only holds files generated from this repository: every run rebuilds it from the
# remote state, so a rejected earlier commit with plain-git PNGs never reaches the push.
# Developed with SI assistance (Claude); reviewed by team #1.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SPACE="${SPACE:-https://huggingface.co/spaces/bymakhmud/SkyBlink}"
OUT="${OUT:-/c/skyblink_deploy/hf-space}"
if [ ! -d "$OUT/.git" ]; then
  git clone "$SPACE" "$OUT"
fi
cd "$OUT"
git fetch -q origin
git reset -q --hard origin/main
git lfs install --local >/dev/null
git lfs track "*.png" "*.jpg" "*.jpeg" "*.gif" "*.ico" "*.webp" >/dev/null
rm -rf backend shared index.html style.css
# tracked files only: no cache, FITS, database or .env
git -C "$ROOT" archive HEAD backend shared | tar -x -C "$OUT"
cp "$ROOT/deploy/huggingface/Dockerfile" "$ROOT/deploy/huggingface/README.md" .
git add -A
git commit -q -m "SkyBlink backend $(git -C "$ROOT" rev-parse --short HEAD)" || echo "nothing new to commit"
echo "PNG files in LFS: $(git lfs ls-files | wc -l)"
echo "Ready in $OUT. Push with:  cd $OUT && git push"
