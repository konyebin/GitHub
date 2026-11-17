#!/usr/bin/env bash
# Create the GitHub repos and push the output of split.sh. Run this yourself:
# it needs a gh login that is allowed to create repositories under OWNER.
#
#   scripts/split-projects/publish.sh [OUT_DIR] [OWNER]
#
# Existing repos are skipped, never overwritten. Pages is switched to the
# "GitHub Actions" source so the bundled workflow can deploy.
set -euo pipefail

OUT="${1:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)/../split-repos}"
OWNER="${2:-konyebin}"

for dir in "$OUT"/*/; do
  name="$(basename "$dir")"
  if gh repo view "$OWNER/$name" >/dev/null 2>&1; then
    echo "skip $OWNER/$name (already exists)"
    continue
  fi
  echo "create $OWNER/$name"
  gh repo create "$OWNER/$name" --public --source "$dir" --remote origin --push
  gh api -X POST "repos/$OWNER/$name/pages" -f build_type=workflow >/dev/null \
    || echo "  could not enable Pages for $name; set Settings > Pages > Source to GitHub Actions"
done
