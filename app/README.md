# StitchDrop.app

A Dock app with a drag-and-drop window for sending designs to your machine.

## Install

From the repo folder:

```bash
bash install.sh app
```

This builds `StitchDrop.app` in `~/Applications` and shows it in Finder. Drag it to your Dock if you like. The app is built on your own Mac rather than downloaded, so macOS doesn't block it.

## Use

1. Click **StitchDrop** in the Dock or in Spotlight. A window opens in your browser.
2. The app finds your machine automatically and shows its free memory. If it can't find it, type the machine's IP address and click **Connect**.
3. Drag `.pes`, `.dst`, `.phc`, `.phx` or `.pen` files onto the drop area, or click the drop area to choose files.
4. Each file shows **Sent ✓**, or the reason it couldn't be sent.

You can close the window and leave the app idle. It quits on its own about 45 seconds after you close the browser tab, or straight away when you click **Quit**. Clicking the Dock icon while it's running just reopens the window.

## How it works

The app runs a small web server on your own Mac at `127.0.0.1:47821`, so only your Mac can reach it, and it rejects requests from other websites. It uses `core/brother_send.py` for the transfer. No Terminal window opens.

## Troubleshooting

- **Nothing happens when I click the icon.** Check `~/Library/Logs/StitchDrop.log`. If it says Python is missing, open Terminal, type `python3`, press Return, and click **Install**.
- **No machine found.** Allow StitchDrop (or Python) under System Settings → Privacy & Security → Local Network, or type the machine's IP address.

## Uninstall

```bash
rm -rf ~/Applications/StitchDrop.app
```
