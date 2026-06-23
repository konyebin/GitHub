#!/usr/bin/env bash
# Rebuild dashboard.bundle.js after editing dashboard modules.
cd "$(dirname "$0")"

LIB=(
  lib/namespace.js
  lib/constants.js
  lib/bia-sanitize.js
  lib/html-utils.js
  lib/note-parser.js
  lib/license-products.js
  lib/bia-slide-matcher.js
  lib/bia-workbook-mapper.js
  lib/bia-portfolio.js
  lib/bia-slide-merger.js
  lib/bia-slide-renderer.js
  lib/bia-slide-editor.js
)

ROOT=(
  schema.js
  checkback-charts.js
  kpi-custom.js
  portfolio-columns.js
  bia-match-aliases.js
  bia-slides.js
  bia-template.js
  account-insight.js
  panel-cache.js
  dashboard-export.js
)

{
  echo '/* auto-generated — run ./build-bundle.sh after editing dashboard modules */'
  for f in "${LIB[@]}" "${ROOT[@]}"; do
    cat "$f"
  done
} > dashboard.bundle.js

echo "Wrote dashboard.bundle.js ($(wc -c < dashboard.bundle.js) bytes)"
