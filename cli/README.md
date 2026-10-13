# `stitchdrop` command

Send designs from Terminal. This is useful for scripts, for troubleshooting, or if you just like the command line.

## Install

From the repo folder:

```bash
bash install.sh cli
```

This installs a `stitchdrop` command into `~/.local/bin`. If that folder isn't on your `PATH`, the installer prints the one line to add to `~/.zshrc`.

You can also skip installing and run the script straight from the repo:

```bash
python3 core/brother_send.py scan
```

## Use

```bash
stitchdrop scan                          # find Brother machines on your Wi-Fi
stitchdrop info   192.168.1.50           # model, embroidery area, firmware (JSON)
stitchdrop status 192.168.1.50           # free memory and the designs on the machine
stitchdrop send   192.168.1.50 a.pes b.dst
```

To skip typing the IP every time, set it once:

```bash
export BROTHER_IP=192.168.1.50
stitchdrop send cover.pes
```

`send` skips files that aren't a machine format, or that don't fit in the machine's free memory. It prints one line per file.

## Uninstall

```bash
rm -f ~/.local/bin/stitchdrop && rm -rf ~/Library/Application\ Support/StitchDrop/cli
```
