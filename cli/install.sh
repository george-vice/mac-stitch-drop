#!/bin/bash
# Installs the `stitchdrop` command (scan / info / status / send).
# Run from the repo:  bash cli/install.sh
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
LIB="$HOME/Library/Application Support/StitchDrop/cli"
BIN="$HOME/.local/bin"
mkdir -p "$LIB" "$BIN"
cp "$SRC/../core/brother_send.py" "$LIB/"
cat > "$BIN/stitchdrop" <<WRAP
#!/bin/bash
exec /usr/bin/env python3 "$LIB/brother_send.py" "\$@"
WRAP
chmod +x "$BIN/stitchdrop"
xattr -cr "$LIB" "$BIN/stitchdrop" 2>/dev/null || true
echo "Installed: $BIN/stitchdrop"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo
     echo "Add it to your PATH (once):"
     echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
esac
echo
echo "Try:  stitchdrop scan"
