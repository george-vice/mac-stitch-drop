#!/bin/bash
# Installs the "Send to Brother" Finder Quick Action.
# Run from the repo:  bash quickaction/install.sh
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
CORE="$SRC/../core"
APP_DIR="$HOME/Library/Application Support/StitchDrop/quickaction"
SERVICES="$HOME/Library/Services"
WF="Send to Brother.workflow"

mkdir -p "$APP_DIR" "$SERVICES" "$HOME/Library/Logs"
cp "$SRC/brother_quicksend.py" "$APP_DIR/"
for f in stitchsend_core.py brother_send.py; do
  cp "$CORE/$f" "$APP_DIR/"
done
rm -rf "$SERVICES/$WF"
cp -R "$SRC/$WF" "$SERVICES/"
xattr -cr "$APP_DIR" "$SERVICES/$WF" 2>/dev/null || true

# Ask macOS to pick up the new Quick Action now instead of after a log-out.
/System/Library/CoreServices/pbs -flush >/dev/null 2>&1 || true
/System/Library/CoreServices/pbs -update >/dev/null 2>&1 || true

echo "Installed:"
echo "  Quick Action: $SERVICES/$WF"
echo "  Scripts:      $APP_DIR"
echo
echo "Right-click a .pes (or .dst/.phc/.phx/.pen, or an Ink/Stitch .svg) in Finder →"
echo "Quick Actions → Send to Brother."
echo
echo "Don't see it? Right-click a file → Quick Actions → Customize…, and tick “Send to Brother”."
