# Ink/Stitch extension: Send to Brother Machine (Wi-Fi)

Send the design you're working on in Inkscape straight to your machine. You don't need to save the file first or export a PES.

## Install

From the repo folder:

```bash
bash install.sh inkstitch
```

Then quit Inkscape fully (⌘Q) and open it again.

The installer copies the extension into Inkscape's extensions folder:
- macOS: `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/send_to_brother/`
- Linux: `~/.config/inkscape/extensions/send_to_brother/`

It also checks that it can find your Ink/Stitch and prints the path it found.

## Use

Choose **Extensions → Ink/Stitch → Visualize and Export → Send to Brother Machine (Wi-Fi)**. A window opens with two steps.

**Step 1: Find your embroidery machine**
- It checks your saved machine first. If you haven't saved one, or the saved one doesn't answer, it searches your Wi-Fi network.
- If it finds several machines, pick one. You can also click **Search network again**, or open **Enter the machine's IP address instead**.
- Click **Next →**. This saves the machine for next time.

**Step 2: Send your design**
- Ink/Stitch starts generating the stitches in the background as soon as the window opens. The result is the same as **File → Save As → Ink/Stitch PES**.
- The window shows the design's size, number of colors and file size. It also checks the design against the machine, for example "✓ Fits the 100 × 100 mm embroidery area".
- **Send to machine** is disabled if the design is too big for the hoop or won't fit in the machine's free memory.
- Options:
  - **Only the selected objects** sends just your current selection.
  - **Also save a .pes copy next to my SVG.** Unsaved documents are saved to `~/Documents/StitchDrop/` instead.

When the send finishes, a **Done** screen confirms it. Then, on the machine, open the embroidery screen and choose the design.

## How it works

- `send_to_brother.inx` registers the menu item.
- `send_to_brother.py` is the entry point Inkscape runs.
- `brother_wizard.py` is the two-step window. It's built with GTK 3, which Inkscape ships for its own Python extensions.
- Stitches come from your installed Ink/Stitch program, which the extension runs as `inkstitch --extension=output --format=pes`. The output is exactly what Ink/Stitch's own export produces.
- If the GTK window can't open, the extension falls back to sending to your saved machine (or one it finds by scanning) and shows the result in a message.

## Troubleshooting

- **The menu item is missing.** Quit Inkscape completely with ⌘Q and reopen it. Then check that the extension folder listed above exists.
- **"Couldn't find Ink/Stitch".** Add the path to the `inkstitch` program to `~/.stitchdrop.json`. On a Mac it's usually inside `inkstitch.app/Contents/MacOS/inkstitch` in your Inkscape extensions folder:
  ```json
  { "inkstitch_path": "/path/to/inkstitch" }
  ```
- **"No Brother machine found".** Allow Inkscape under System Settings → Privacy & Security → Local Network, or enter the machine's IP address.

## Uninstall

```bash
rm -rf ~/Library/Application\ Support/org.inkscape.Inkscape/config/inkscape/extensions/send_to_brother
```
