#!/usr/bin/env python3
"""Finder Quick Action: Send to Brother.

Right-click files in Finder → Quick Actions → Send to Brother.
  Step 1: find the machine (saved one, else scan; pick if several; or type an IP)
  Step 2: confirm, then send. Embroidery files go as-is; .svg files are
          stitched with your installed Ink/Stitch first.
Uses native macOS dialogs via osascript. Python 3 standard library only.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stitchsend_core as core  # noqa: E402

TITLE = "Send to Brother"
MACHINE_EXTS = {".pes", ".phc", ".phx", ".dst", ".pen"}
OSA = shutil.which("osascript") or "/usr/bin/osascript"


# ------------------------------------------------------------------ dialogs
def _q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def osa(script):
    """Run AppleScript; return stdout, or None if the user cancelled."""
    r = subprocess.run([OSA, "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        return None          # "User canceled" (-128) or a dialog error
    return r.stdout.strip()


def dialog(text, buttons=("OK",), default=None, icon="note"):
    btns = "{" + ", ".join(_q(b) for b in buttons) + "}"
    out = osa(f"display dialog {_q(text)} with title {_q(TITLE)} buttons {btns} "
              f"default button {_q(default or buttons[-1])} with icon {icon}")
    if out is None:
        return None
    return out.split("button returned:", 1)[-1].split(",")[0].strip()


def ask_text(text, default=""):
    out = osa(f"display dialog {_q(text)} with title {_q(TITLE)} default answer {_q(default)} "
              f"buttons {{\"Cancel\", \"Connect\"}} default button \"Connect\"")
    if out is None:
        return None
    return out.split("text returned:", 1)[-1].strip()


def choose(prompt, items):
    lst = "{" + ", ".join(_q(i) for i in items) + "}"
    out = osa(f"choose from list {lst} with title {_q(TITLE)} with prompt {_q(prompt)} "
              f"default items {{{_q(items[0])}}} OK button name \"Use this machine\"")
    if not out or out == "false":
        return None
    return items.index(out) if out in items else None


def notify(text):
    osa(f"display notification {_q(text)} with title {_q(TITLE)}")


def stop(text, icon="caution"):
    dialog(text, ("OK",), icon=icon)
    sys.exit(0)


# ------------------------------------------------------------------ step 1
def machine_label(m):
    bits = [m["name"], m["ip"]]
    if "area_mm" in m:
        bits.append(f"{m['area_mm'][0]:.0f}×{m['area_mm'][1]:.0f} mm")
    return " · ".join(bits)


def find_machine(force_search=False):
    """Step 1. Returns a machine dict, or exits if the user cancels."""
    if not force_search:
        saved = core.load_cfg().get("ip")
        if saved:
            m = core.probe(saved)
            if m:
                return m
            notify(f"Saved machine at {saved} didn't answer. Searching your network…")
        else:
            notify("Searching your Wi-Fi network for your Brother machine…")
    else:
        notify("Searching your Wi-Fi network…")

    found = core.scan_network()
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        i = choose("Which machine should designs go to?", [machine_label(m) for m in found])
        if i is None:
            sys.exit(0)
        return found[i]

    # nothing found → offer manual IP
    while True:
        pick = dialog("Couldn't find a Brother machine on your network.\n\n" + core.NOT_FOUND_HELP,
                      ("Cancel", "Search again", "Enter IP…"), default="Enter IP…", icon="caution")
        if pick in (None, "Cancel"):
            sys.exit(0)
        if pick == "Search again":
            return find_machine(force_search=True)
        ip = ask_text("Machine IP address (shown on the machine under Settings → Wireless LAN):")
        if not ip:
            continue
        m = core.probe(ip)
        if m:
            return m
        dialog(f"No Brother machine answered at {ip}.", ("OK",), icon="caution")


# ------------------------------------------------------------------ step 2
def prepare(paths):
    """Turn selected files into [(name, pes_bytes_or_None, facts, note)]; collect skips."""
    jobs, skipped = [], []
    for p in paths:
        base, ext = os.path.splitext(os.path.basename(p))
        ext = ext.lower()
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in base).strip("_") or "design"
        if ext in MACHINE_EXTS:
            with open(p, "rb") as f:
                data = f.read()
            jobs.append((safe, ext, data, core.pes_facts(data) if ext == ".pes" else {"kb": len(data) / 1024}))
        elif ext == ".svg":
            notify(f"Generating stitches for {base} with Ink/Stitch…")
            try:
                data = core.export_pes(p)
            except core.UserError as e:
                skipped.append(f"{os.path.basename(p)}: {e}")
                continue
            jobs.append((safe, ".pes", data, core.pes_facts(data)))
        elif os.path.isdir(p):
            skipped.append(f"{os.path.basename(p)}: folders aren't supported")
        else:
            skipped.append(f"{os.path.basename(p)}: not an embroidery file (.pes .dst .phc .phx .pen) or .svg")
    return jobs, skipped


def describe(job):
    name, ext, _data, f = job
    bits = [name + ext]
    if "width_mm" in f:
        bits.append(f"{f['width_mm']:.0f}×{f['height_mm']:.0f} mm")
    bits.append(f"{f['kb']:.0f} KB" if f["kb"] >= 10 else f"{f['kb']:.1f} KB")
    return " · ".join(bits)


def main(paths):
    usable = [p for p in paths if os.path.splitext(p)[1].lower() in MACHINE_EXTS | {".svg"}]
    if not usable:
        stop("Select one or more embroidery files (.pes .dst .phc .phx .pen) "
             "or Ink/Stitch .svg files in Finder first.")

    # Step 1: find the machine
    machine = find_machine()

    jobs, skipped = prepare(paths)

    while True:
        ok, blocked = [], []
        for j in jobs:
            problem = core.fit_problem(j[3], machine)
            (blocked if problem else ok).append((j, problem))
        if not ok:
            lines = [f"• {describe(j)}\n   {p}" for j, p in blocked] + [f"• {s}" for s in skipped]
            stop("Nothing can be sent to " + machine_label(machine) + ".\n\n" + "\n".join(lines))

        # Step 2: confirm and send
        text = f"Send to {machine['name']} at {machine['ip']}?\n\n"
        text += "\n".join(f"✓ {describe(j)}" for j, _ in ok)
        if blocked or skipped:
            text += "\n\nWon't be sent:\n" + "\n".join(
                [f"✗ {describe(j)} — {p}" for j, p in blocked] + [f"✗ {s}" for s in skipped])
        pick = dialog(text, ("Cancel", "Change machine…", "Send"), default="Send")
        if pick in (None, "Cancel"):
            sys.exit(0)
        if pick == "Change machine…":
            machine = find_machine(force_search=True)
            continue
        break

    core.remember_machine(machine)        # confirmed by pressing Send
    sent, failed = [], []
    for (name, ext, data, _f), _ in ok:
        try:
            if ext == ".pes":
                core.send(machine, name, data)
            else:
                core.send_raw(machine, name + ext, data)
            sent.append(name + ext)
        except core.UserError as e:
            failed.append(f"{name}{ext}: {e}")

    if failed:
        dialog(f"Sent {len(sent)} of {len(ok)} to {machine['name']}.\n\nFailed:\n" + "\n".join(failed),
               ("OK",), icon="caution")
    else:
        what = sent[0] if len(sent) == 1 else f"{len(sent)} designs"
        notify(f"✓ Sent {what} to {machine['name']}. Choose {'it' if len(sent) == 1 else 'them'} on the machine's embroidery screen.")


if __name__ == "__main__":
    try:
        main([a for a in sys.argv[1:] if a])
    except SystemExit:
        raise
    except Exception as e:
        dialog(f"Something went wrong: {e}", ("OK",), icon="stop")
