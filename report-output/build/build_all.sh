#!/usr/bin/env bash
# Full pipeline: diagrams/assets (optional) -> DOCX -> PDF -> page map -> DOCX again -> PDF again -> stability check.
# Usage: ./build_all.sh [--assets]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SP=/private/tmp/claude-501/-Users-naytikgoyal--claude-spares-spare-nPXQeR/20fbe208-e352-431d-b787-3773582913ae/scratchpad
export NODE_PATH="$SP/node-tools/node_modules" PLAYWRIGHT_BROWSERS_PATH="$SP/pw-browsers" PYTHONDONTWRITEBYTECODE=1
export FONTCONFIG_FILE="$HERE/fonts.conf"
SOFFICE="$HOME/Applications/LibreOffice.app/Contents/MacOS/soffice"
OUT="$HERE/../output"; NAME="Cybersecurity_Project_Report_Naytik_Goyal"
cd "$HERE"
python3 -c "import json,refs_data; json.dump(refs_data.REFS, open('refs.json','w'), ensure_ascii=False, indent=1)"
if [ "${1:-}" = "--assets" ]; then
  "$SP/test-venv/bin/python" make_diagrams.py
  "$SP/test-venv/bin/python" make_assets.py
fi
topdf() { "$SOFFICE" --headless -env:UserInstallation=file:///tmp/lo-report-profile --convert-to pdf --outdir "$OUT" "$1" >/dev/null 2>&1; }
rm -f pagemap.json
for pass in 1 2 3; do
  node build.js "$OUT/$NAME.docx"
  topdf "$OUT/$NAME.docx"
  cp pagemap.json pagemap.prev.json 2>/dev/null || echo '{}' > pagemap.prev.json
  "$SP/tools-venv/bin/python" -I pagemap.py "$OUT/$NAME.pdf"
  if cmp -s pagemap.json pagemap.prev.json; then echo "page map stable after pass $pass"; break; fi
done
rm -f pagemap.prev.json
ls -la "$OUT" | awk '{print $5, $NF}'
