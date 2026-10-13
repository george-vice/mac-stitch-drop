# Mac Stitch Drop

Send embroidery designs from your Mac to a Brother Wi-Fi embroidery machine. You don't need a USB stick, a Windows PC, or your phone.

Brother's own Wi-Fi transfer app, *Design Database Transfer*, only runs on Windows. Mac Stitch Drop talks to the machine directly over your home network, using the same protocol Brother's app uses. You can send from wherever you are working:

| Tool | How you send | Install |
|---|---|---|
| **[Finder Quick Action](quickaction/)** | Right-click files → **Quick Actions → Send to Brother** | `bash install.sh quickaction` |
| **[Ink/Stitch extension](inkstitch/)** | In Inkscape: **Extensions → Ink/Stitch → Visualize and Export → Send to Brother Machine** | `bash install.sh inkstitch` |
| **[StitchDrop.app](app/)** | Click the Dock icon, then drag files onto the window | `bash install.sh app` |
| **[`stitchdrop` command](cli/)** | `stitchdrop send design.pes` in Terminal | `bash install.sh cli` |

**Website:** https://george-vice.github.io/mac-stitch-drop/

## Quick start

```bash
git clone https://github.com/george-vice/mac-stitch-drop.git
cd mac-stitch-drop
bash install.sh quickaction     # or: inkstitch, app, cli, all
```

You can also download the repo as a ZIP (green **Code** button → **Download ZIP**), unzip it, and run the same command from inside the folder.

## What every tool does

- **Finds your machine automatically.** It scans your Wi-Fi network for Brother machines that accept designs. You can also type the machine's IP address yourself; the machine shows it under Settings → Wireless LAN.
- **Remembers your machine.** All four tools share one settings file, `~/.stitchdrop.json`. Set up the machine in one tool and the others already know it.
- **Checks before sending.** It refuses designs that are bigger than the machine's embroidery area, or that won't fit in its free memory, and tells you why.
- **Sends** `.pes`, `.dst`, `.phc`, `.phx` and `.pen` files as they are. The Quick Action and the Ink/Stitch extension can also send Ink/Stitch `.svg` designs; your installed Ink/Stitch generates the stitches first.

On the machine, open the embroidery screen and choose the design you received.

## Requirements

- macOS 11 or newer.
- Python 3. Macs prompt you to install it the first time you run `python3` in Terminal.
- A Brother (or Baby Lock) embroidery machine with Wi-Fi that works with Brother's *Design Database Transfer* app.
- For `.svg` designs: [Inkscape](https://inkscape.org) with [Ink/Stitch](https://inkstitch.org).

**Tested on:** Brother SE700. Other Wi-Fi models that work with Design Database Transfer should behave the same, but haven't been confirmed. If you try another model, please [open an issue](https://github.com/george-vice/mac-stitch-drop/issues) and say how it went.

**First run:** macOS asks whether to allow access to devices on your local network. Choose **Allow**, or the tool can't find the machine. You can change this later under System Settings → Privacy & Security → Local Network.

## Repo layout

```
core/          brother_send.py      the Wi-Fi protocol, plus a command-line interface
               stitchsend_core.py   shared logic: Ink/Stitch export, PES checks, discovery
quickaction/   Finder Quick Action
inkstitch/     Inkscape / Ink/Stitch extension
app/           StitchDrop.app
cli/           installer for the `stitchdrop` command
docs/          the GitHub Pages website
```

The [core README](core/) describes the protocol.

## Credits

- The Brother Wi-Fi protocol details come from the open-source reverse-engineering in [Ember Bridge](https://github.com/EmberSoftwareInc/ember-bridge) (MIT) and [Lilo](https://github.com/Kadwood/lilo) (GPL-3.0). This project is an independent Python implementation of that protocol.
- The PES/PEC file layout follows [pyembroidery](https://github.com/EmbroidePy/pyembroidery).
- [Ink/Stitch](https://inkstitch.org) does all the stitch generation for `.svg` designs.

## Disclaimer

This is an unofficial hobby project. It is not affiliated with, endorsed by, or supported by Brother Industries. "Brother" is a trademark of its owner and is used here only to say which machines this works with. A Brother firmware update could change the protocol at any time. Use at your own risk.

## License

[MIT](LICENSE)
