#!/bin/bash
# Installs "Send to Brother Machine (Wi-Fi)" into Inkscape's extensions folder.
# Run from the repo:  bash inkstitch/install.sh
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
CORE="$SRC/../core"
case "$(uname)" in
  Darwin) EXT="$HOME/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions" ;;
  *)      EXT="$HOME/.config/inkscape/extensions" ;;
esac
DEST="$EXT/send_to_brother"

rm -rf "$DEST"                      # clears older versions
mkdir -p "$DEST"
cp "$SRC/send_to_brother.inx" "$SRC/send_to_brother.py" "$SRC/brother_wizard.py" "$DEST/"
cp "$CORE/stitchsend_core.py" "$CORE/brother_send.py" "$DEST/"
xattr -cr "$DEST" 2>/dev/null || true
echo "Installed to: $DEST"

FOUND="$(/usr/bin/env python3 - "$DEST" <<'PY' 2>/dev/null || true
import sys; sys.path.insert(0, sys.argv[1])
import stitchsend_core as c
try:
    print(" ".join(c.find_inkstitch()))
except Exception:
    pass
PY
)"
if [ -n "$FOUND" ]; then
  echo "Found Ink/Stitch: $FOUND"
else
  echo "Note: couldn't locate Ink/Stitch automatically. Add its path to ~/.stitchdrop.json as"
  echo "      \"inkstitch_path\" (see inkstitch/README.md)."
fi
echo
echo "Restart Inkscape (⌘Q), then: Extensions → Ink/Stitch → Visualize and Export → Send to Brother Machine (Wi-Fi)"
