#!/usr/bin/env python3
"""brother_send.py — send embroidery files to a Brother Wi-Fi machine from a Mac.

Speaks the "pedxml" protocol used by Brother's Windows-only
Design Database Transfer app (HTTPS on port 443, self-signed cert, no pairing).
Protocol details come from the open-source reverse-engineering in
Ember Bridge / Lilo (github.com/Kadwood/lilo, app/src-tauri/src/brother).

Python 3 standard library only. Usage:
    python3 brother_send.py scan                      # find machines on your Wi-Fi
    python3 brother_send.py info   192.168.1.50       # model, hoop size, firmware
    python3 brother_send.py status 192.168.1.50       # free memory + files on machine
    python3 brother_send.py send   192.168.1.50 a.pes b.pes
Tip: set BROTHER_IP=192.168.1.50 and omit the IP argument.
"""
import concurrent.futures as cf
import http.client
import ipaddress
import json
import os
import re
import secrets
import socket
import ssl
import subprocess
import sys

UA = "Design Database Transfer"   # machine only answers the official client
APP_ID = "23"
SEWING = "/sewing/sewing.cgi"
EXTS = {".pes", ".phc", ".phx", ".dst", ".pen"}

# The machine uses a self-signed certificate, so verification must be off.
# This only ever talks to an IP on your own LAN.
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

SCHEME = os.environ.get("BROTHER_SCHEME", "https")  # "http" only for local testing
PORT = int(os.environ.get("BROTHER_PORT", "443" if SCHEME == "https" else "80"))


def _conn(ip, timeout):
    if SCHEME == "http":
        return http.client.HTTPConnection(ip, PORT, timeout=timeout)
    return http.client.HTTPSConnection(ip, PORT, timeout=timeout, context=_CTX)


def _request(ip, method, path, body=None, headers=None, timeout=10):
    h = {"User-Agent": UA, "Accept-Language": "1046", "Cache-Control": "no-cache"}
    h.update(headers or {})
    c = _conn(ip, timeout)
    try:
        c.request(method, path, body=body, headers=h)
        r = c.getresponse()
        return r.status, r.read()
    finally:
        c.close()


def get_info(ip, timeout=5):
    status, data = _request(ip, "GET", "/info", timeout=timeout)
    if status != 200:
        raise RuntimeError(f"GET /info answered HTTP {status}")
    return json.loads(data)


def _tag(xml, name):
    m = re.search(rf"<{name}>(.*?)</{name}>", xml, re.S)
    return m.group(1).strip() if m else None


def get_status(ip):
    body = f"req_sessionid=0&req_appid={APP_ID}&req_appver=1.2.0&req_appstate=2"
    status, data = _request(ip, "POST", SEWING, body=body.encode(),
                            headers={"Content-Type": "application/x-www-form-urlencoded"})
    xml = data.decode("utf-8", "replace")
    code = _tag(xml, "error_code")
    if status != 200 or code is None:
        raise RuntimeError(f"status call failed (HTTP {status}): {xml[:200]}")
    if code != "0":
        raise RuntimeError(f"machine rejected status request, error_code={code}")
    return {
        "total": int(_tag(xml, "upload_size") or 0),
        "free": int(_tag(xml, "upload_freesize") or 0),
        "files": re.findall(r"<file_name>(.*?)</file_name>", xml),
    }


def send_file(ip, path):
    with open(path, "rb") as f:
        design = f.read()
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(path))
    boundary = "-" * 27 + secrets.token_hex(6)
    params = f"req_sessionid=0&req_appid={APP_ID}&req_appver=100&req_appstate=3"
    crlf = b"\r\n"
    # Built by hand on purpose: the firmware wants the exact (nonstandard)
    # header spacing the official client sends.
    body = b"".join([
        b"--", boundary.encode(), crlf,
        b'Content-Disposition:form-data;name="req_parameter";filename="req_parameter"', crlf,
        b"Content-Type:application/x-www-form-urlencoded", crlf, crlf,
        params.encode(), crlf,
        b"--", boundary.encode(), crlf,
        b'Content-Disposition:form-data;name="myfile";filename="', name.encode(), b'"', crlf,
        b"Content-Type:application/octet-stream", crlf, crlf,
        design, crlf,
        b"--", boundary.encode(), b"--", crlf,
    ])
    status, data = _request(ip, "POST", SEWING, body=body, timeout=60, headers={
        "Content-Type": f"multipart/form-data;boundary={boundary}",
        "Content-Length": str(len(body)),
        "Accept-Encoding": "gzip,deflate",
        "Connection": "Keep-Alive",
    })
    if status not in (200, 204):
        raise RuntimeError(f"upload of {name} failed: HTTP {status} {data[:200]!r}")


def _local_subnets():
    """Private /24s for this Mac's active interfaces (en0 = Wi-Fi usually)."""
    nets = set()
    try:
        out = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
        ips = re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", out)
    except FileNotFoundError:
        ips = [socket.gethostbyname(socket.gethostname())]
    for ip in ips:
        a = ipaddress.ip_address(ip)
        if a.is_private and not a.is_loopback and not a.is_link_local:
            nets.add(ipaddress.ip_network(f"{ip}/24", strict=False))
    return sorted(nets)


def _probe(ip):
    try:
        with socket.create_connection((ip, PORT), timeout=0.6):
            pass
        info = get_info(ip, timeout=3)
        return (ip, info) if "pedxml" in info.get("apis", {}) else None
    except Exception:
        return None


def scan():
    nets = _local_subnets()
    if not nets:
        sys.exit("No private network found. Is Wi-Fi on?")
    hosts = [str(h) for n in nets for h in n.hosts()]
    print(f"Scanning {', '.join(map(str, nets))} ({len(hosts)} addresses)…")
    found = []
    with cf.ThreadPoolExecutor(64) as pool:
        for hit in pool.map(_probe, hosts):
            if hit:
                found.append(hit)
                ip, info = hit
                print(f"  ✓ {ip}  name={info.get('name')!r}  fw={info.get('version')}")
    if not found:
        print("No Brother machine found. Check the machine is on, joined to the same Wi-Fi, "
              "and that macOS allowed Terminal 'Local Network' access.")
    return found


def _ip(args):
    if args:
        return args.pop(0)
    if os.environ.get("BROTHER_IP"):
        return os.environ["BROTHER_IP"]
    sys.exit("Give the machine's IP (run `scan` first) or set BROTHER_IP.")


def main(argv):
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "scan":
        scan()
    elif cmd == "info":
        print(json.dumps(get_info(_ip(args)), indent=2))
    elif cmd == "status":
        s = get_status(_ip(args))
        print(f"Free memory: {s['free']:,} of {s['total']:,} bytes")
        print("Files on machine:", ", ".join(s["files"]) or "(none)")
    elif cmd == "send":
        if args and os.path.isfile(args[0]) and not os.environ.get("BROTHER_IP"):
            sys.exit("Usage: send <ip> <file> [file…]")
        ip = _ip(args)
        if not args:
            sys.exit("Name at least one .pes file.")
        free = get_status(ip)["free"]
        for path in args:
            ext = os.path.splitext(path)[1].lower()
            if ext not in EXTS:
                print(f"  skip {path}: {ext} isn't a format the machine takes")
                continue
            size = os.path.getsize(path)
            if size > free:
                print(f"  skip {path}: {size:,} bytes but only {free:,} free on machine")
                continue
            send_file(ip, path)
            free -= size
            print(f"  ✓ sent {os.path.basename(path)} ({size:,} bytes)")
        print("Done. On the SE700, open the embroidery screen and pick the Wi-Fi/received designs.")
    else:
        sys.exit(f"Unknown command {cmd!r}. Try: scan, info, status, send")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, RuntimeError) as e:
        sys.exit(f"Error: {e}")
