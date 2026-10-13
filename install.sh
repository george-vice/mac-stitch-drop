#!/bin/bash
# Install one or more Mac Stitch Drop tools.
#   bash install.sh quickaction    Finder right-click → Send to Brother
#   bash install.sh inkstitch      Inkscape / Ink/Stitch extension
#   bash install.sh app            StitchDrop.app (drag-and-drop window)
#   bash install.sh cli            `stitchdrop` terminal command
#   bash install.sh all            everything
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
TOOLS=("$@")
if [ ${#TOOLS[@]} -eq 0 ]; then
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi
[ "${TOOLS[0]}" = "all" ] && TOOLS=(quickaction inkstitch app cli)
for t in "${TOOLS[@]}"; do
  case "$t" in
    quickaction|inkstitch|app|cli) echo "== Installing $t"; bash "$ROOT/$t/install.sh"; echo ;;
    *) echo "Unknown tool: $t (choose quickaction, inkstitch, app, cli or all)"; exit 1 ;;
  esac
done
