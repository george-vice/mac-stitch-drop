"""Non-GUI logic for the Brother Wi-Fi extension: Ink/Stitch export, PES
inspection, machine discovery and upload. Errors are raised as UserError with
a message written for the person using Inkscape."""
import concurrent.futures as cf
import json
import os
import re
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brother_send as bs  # noqa: E402

CONFIG = os.path.expanduser("~/.stitchdrop.json")   # shared with StitchDrop.app

NOT_FOUND_HELP = ("• Is the machine switched on and joined to the same Wi-Fi as this computer?\n"
                  "• On a Mac, allow Inkscape under System Settings → Privacy & Security → Local Network.\n"
                  "• Or enter the machine's IP (shown on the machine under Settings → Wireless LAN).")


class UserError(Exception):
    pass


# ------------------------------------------------------------------ settings
def load_cfg():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(update):
    cfg = load_cfg()
    cfg.update(update)
    try:
        with open(CONFIG, "w") as f:
            json.dump(cfg, f)
    except OSError:
        pass


def remember_machine(machine):
    save_cfg({"ip": machine["ip"], "name": machine["name"]})


# ------------------------------------------------------------------ Ink/Stitch
def _candidates(root, depth=4):
    if not root or not os.path.isdir(root):
        return
    root = os.path.abspath(root)
    base = root.count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count(os.sep) - base >= depth:
            dirnames[:] = []
        if dirpath.endswith(os.path.join("Contents", "MacOS")) and "inkstitch" in filenames:
            yield [os.path.join(dirpath, "inkstitch")]
        elif os.path.basename(dirpath) == "bin":
            for name in ("inkstitch", "inkstitch.exe"):
                if name in filenames and "inkstitch" in dirpath.lower():
                    yield [os.path.join(dirpath, name)]
        if "inkstitch.py" in filenames and os.path.isdir(os.path.join(dirpath, "lib", "extensions")):
            yield [sys.executable, os.path.join(dirpath, "inkstitch.py")]


def find_inkstitch():
    override = load_cfg().get("inkstitch_path", "")
    if override:
        override = os.path.expanduser(override)
        if os.path.isfile(override):
            return [sys.executable, override] if override.endswith(".py") else [override]
    roots = [
        os.path.dirname(HERE),
        os.path.expanduser("~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions"),
        os.path.expanduser("~/.config/inkscape/extensions"),
        os.path.join(os.environ.get("APPDATA", ""), "inkscape", "extensions"),
        "/Applications/Inkscape.app/Contents/Resources/share/inkscape/extensions",
    ]
    seen = set()
    for r in roots:
        if r in seen:
            continue
        seen.add(r)
        for cmd in _candidates(r):
            if os.access(cmd[-1], os.R_OK):
                return cmd
    raise UserError("Couldn't find Ink/Stitch. Install Ink/Stitch, or put the path to its "
                    f"'inkstitch' program in {CONFIG} as \"inkstitch_path\".")


def export_pes(svg_path, ids=()):
    cmd = find_inkstitch() + ["--extension=output", "--format=pes"] + [f"--id={i}" for i in ids] + [svg_path]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise UserError("Ink/Stitch took more than 10 minutes to generate stitches, so I stopped.")
    except OSError as e:
        raise UserError(f"Couldn't run Ink/Stitch ({e}).")
    if r.stdout.startswith(b"#PES"):
        return r.stdout
    detail = r.stderr.decode("utf-8", "replace").strip()[-600:]
    if not r.stdout and not detail:
        raise UserError("Nothing to stitch. Make sure the design has Ink/Stitch objects "
                        "(fills, satins or running stitches) that aren't hidden"
                        + (", or untick “Only the selected objects”." if ids else "."))
    raise UserError("Ink/Stitch couldn't export this design:\n" + (detail or "(no details)"))


# ------------------------------------------------------------------ PES facts
def pes_facts(data):
    """{'kb', 'width_mm', 'height_mm', 'colors'} read from the PEC header."""
    facts = {"kb": len(data) / 1024}
    try:
        off = struct.unpack_from("<I", data, 8)[0]
        if data[off:off + 3] == b"LA:":
            facts["colors"] = data[off + 48] + 1
            w, h = struct.unpack_from("<HH", data, off + 512 + 8)
            facts["width_mm"], facts["height_mm"] = w / 10.0, h / 10.0
    except (struct.error, IndexError):
        pass
    return facts


def document_info(svg_path):
    """(real .svg path or None, safe design name)."""
    real = os.environ.get("DOCUMENT_PATH") or None
    name = None
    try:
        with open(svg_path, "rb") as f:
            head = f.read(200_000).decode("utf-8", "replace")
        m = re.search(r'sodipodi:docname="([^"]+)"', head)
        if m:
            name = m.group(1)
    except OSError:
        pass
    if real:
        name = os.path.basename(real)
    name = os.path.splitext(name or "design")[0]
    return real, re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "design"


# ------------------------------------------------------------------ machine
def machine_from(ip, info):
    feat = info.get("features") or {}
    m = {"ip": ip, "name": info.get("name") or "Brother machine", "firmware": info.get("version")}
    if feat.get("embwidth") and feat.get("embheight"):
        m["area_mm"] = (feat["embwidth"] / 10.0, feat["embheight"] / 10.0)
    try:
        st = bs.get_status(ip)
        m["free_kb"], m["total_kb"], m["files"] = st["free"] // 1024, st["total"] // 1024, len(st["files"])
    except Exception:
        pass
    return m


def probe(ip):
    """Machine dict if a Brother design-transfer machine answers at ip, else None."""
    try:
        info = bs.get_info(ip, timeout=4)
    except Exception:
        return None
    return machine_from(ip, info) if "pedxml" in info.get("apis", {}) else None


def scan_network(on_progress=None):
    hosts = [str(h) for n in bs._local_subnets() for h in n.hosts()]
    found, done = [], 0
    with cf.ThreadPoolExecutor(64) as pool:
        for hit in pool.map(bs._probe, hosts):
            done += 1
            if on_progress and done % 16 == 0:
                on_progress(done, len(hosts))
            if hit:
                found.append(machine_from(*hit))
    return found


def fit_problem(facts, machine):
    """None if the design fits, else a sentence explaining why not."""
    if "width_mm" in facts and "area_mm" in machine:
        w, h = facts["width_mm"], facts["height_mm"]
        mw, mh = machine["area_mm"]
        if not ((w <= mw and h <= mh) or (w <= mh and h <= mw)):
            return f"Too big: the design is {w:.0f} × {h:.0f} mm, the hoop area is {mw:.0f} × {mh:.0f} mm."
    if "free_kb" in machine and facts["kb"] > machine["free_kb"]:
        return f"Not enough memory on the machine ({machine['free_kb']} KB free). Delete some designs on it first."
    return None


def send(machine, name, pes):
    send_raw(machine, name + ".pes", pes)


def send_raw(machine, filename, data):
    """Send any machine-format file (.pes .dst .phc .phx .pen), keeping its extension."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, filename)
        with open(path, "wb") as f:
            f.write(data)
        try:
            bs.send_file(machine["ip"], path)
        except Exception as e:
            raise UserError(f"Sending failed: {e}")


def save_copy(real_svg_path, name, pes):
    folder = os.path.dirname(real_svg_path) if real_svg_path else os.path.expanduser("~/Documents/StitchDrop")
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, name + ".pes")
    with open(out, "wb") as f:
        f.write(pes)
    return out
