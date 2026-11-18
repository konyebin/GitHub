#!/usr/bin/env bash
# Build one standalone git repo per project, keeping each project's history.
#
#   scripts/split-projects/split.sh [OUT_DIR] [project ...]
#
# OUT_DIR defaults to ../split-repos next to this checkout. Nothing in this
# checkout is modified. Requires git-filter-repo (pip install git-filter-repo).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(git -C "$HERE" rev-parse --show-toplevel)"
OUT="${1:-$SRC/../split-repos}"
shift || true

ALL_PROJECTS=(quiz-bank ice-breaker misc-ops-report ai-receptionist ctfmonopoly hiring-analysis influence-skills)
PROJECTS=("${@:-${ALL_PROJECTS[@]}}")

command -v git-filter-repo >/dev/null || { echo "git-filter-repo not found (pip install git-filter-repo)" >&2; exit 1; }
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

demo_dir() { echo "docs/public/demos/$1/"; }

filter_args() {
  case "$1" in
    quiz-bank)
      echo --path "$(demo_dir quiz-bank)" --path quiz-bank/tests/ --path quiz-bank/docs/ \
        --path-rename "$(demo_dir quiz-bank):" \
        --path-rename quiz-bank/tests/:tests/ \
        --path-rename quiz-bank/docs/:docs/
      ;;
    *)
      echo --path "$(demo_dir "$1")" --path-rename "$(demo_dir "$1"):"
      ;;
  esac
}

fix_quiz_bank() {
  sed -i 's#"\.\./\.\./docs/public/demos/quiz-bank/#"../#' tests/*.test.js
  sed -i 's#docs/public/demos/quiz-bank/quizzes\.json#quizzes.json#' tests/publish.test.js app.js
  sed -i 's#repo: "GitHub"#repo: "quiz-bank"#' app.js
  sed -i 's#github.com/konyebin/GitHub/actions#github.com/konyebin/quiz-bank/actions#' app.js
  sed -i 's#Deploy docs to GitHub Pages#Deploy to GitHub Pages#' app.js
}

for name in "${PROJECTS[@]}"; do
  dest="$OUT/$name"
  echo "==> $name"
  rm -rf "$dest"
  git clone --quiet --no-local "$SRC" "$dest"
  (
    cd "$dest"
    # shellcheck disable=SC2046
    git filter-repo --quiet --force $(filter_args "$name")

    cp -a "$HERE/overlays/_common/." .
    [ -d "$HERE/overlays/$name" ] && cp -a "$HERE/overlays/$name/." .
    [ "$name" = quiz-bank ] && fix_quiz_bank
    [ -f prepare-github-pages.sh ] && chmod +x prepare-github-pages.sh

    git add -A
    git commit --quiet -m "Make $name a standalone repository" \
      -m "Adds README, .gitignore and a GitHub Pages workflow, and removes paths that assumed the GitHub monorepo layout."
  )
done

echo
echo "Standalone repos written to $OUT"
