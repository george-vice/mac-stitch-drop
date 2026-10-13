#!/bin/bash
# Builds StitchDrop.app in your Applications folder.
# Run from the repo:  bash app/install.sh
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
CORE="$SRC/../core"
DEST="$HOME/Applications/StitchDrop.app"

echo "Building StitchDrop.app…"
mkdir -p "$HOME/Applications"
rm -rf "$DEST"
mkdir -p "$DEST/Contents/MacOS" "$DEST/Contents/Resources"

# (the quarantine flag is cleared below, so macOS will not block the app)
cp "$SRC/brother_gui.py" "$CORE/brother_send.py" "$DEST/Contents/Resources/"
cp "$SRC/StitchDrop.icns" "$DEST/Contents/Resources/StitchDrop.icns"

cat > "$DEST/Contents/MacOS/StitchDrop" <<'LAUNCH'
#!/bin/bash
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
for P in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$P" ] && "$P" -c 'import sys' >/dev/null 2>&1; then
    exec "$P" "$RES/brother_gui.py" >>"$HOME/Library/Logs/StitchDrop.log" 2>&1
  fi
done
osascript -e 'display alert "StitchDrop needs Python 3" message "Open Terminal, type python3 and press Return, then click Install. Afterwards open StitchDrop again."'
LAUNCH
chmod +x "$DEST/Contents/MacOS/StitchDrop"

cat > "$DEST/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>StitchDrop</string>
  <key>CFBundleDisplayName</key><string>StitchDrop</string>
  <key>CFBundleIdentifier</key><string>local.stitchdrop</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>StitchDrop</string>
  <key>CFBundleIconFile</key><string>StitchDrop</string>
  <key>LSUIElement</key><true/>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSLocalNetworkUsageDescription</key><string>StitchDrop looks for your Brother embroidery machine on your Wi-Fi.</string>
</dict></plist>
PLIST

xattr -cr "$DEST" 2>/dev/null || true
touch "$DEST"   # nudge Finder to pick up the icon

echo "Done → $DEST"
echo "Opening it in Finder. Drag it to your Dock if you like."
open -R "$DEST" 2>/dev/null || true
