#!/usr/bin/env bash
# Run from this repo AFTER publish.sh and after each new Pages site is live.
# Removes the split-out projects from the monorepo and points the docs hub at
# their own sites. Review `git diff` and commit yourself.
set -euo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$ROOT"
IDS=(quiz-bank ice-breaker misc-ops-report ai-receptionist ctfmonopoly hiring-analysis influence-skills)

for id in "${IDS[@]}"; do
  files=$(grep -rlE "demos/$id/|docs/public/demos/$id" docs README.md AGENTS.md CLAUDE.md .github \
    --include=*.md --include=*.json --include=*.vue --include=*.ts --include=*.yml \
    --exclude-dir=node_modules --exclude-dir=public --exclude-dir=dist --exclude-dir=cache 2>/dev/null || true)
  for f in $files; do
    sed -i -E \
      -e "s#https://konyebin\.github\.io/GitHub/demos/$id/#https://konyebin.github.io/$id/#g" \
      -e "s#\]\(/demos/$id/#](https://konyebin.github.io/$id/#g" \
      -e "s#\"/demos/$id/#\"https://konyebin.github.io/$id/#g" \
      -e "s#(bash )?(~/Documents/GitHub/)?docs/public/demos/$id/prepare-github-pages\.sh#git clone https://github.com/konyebin/$id \&\& bash $id/prepare-github-pages.sh#g" \
      -e "s#docs/public/demos/$id/#https://github.com/konyebin/$id#g" \
      "$f"
  done
  git rm -rq --ignore-unmatch "docs/public/demos/$id"
done

git rm -rq --ignore-unmatch quiz-bank
sed -i '/Prepare Misc Ops report demo for GitHub Pages/,+2d' .github/workflows/deploy-docs.yml

echo "Done. Review with: git status && git diff"
