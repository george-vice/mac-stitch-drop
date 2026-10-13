# core

Shared code that every tool installs a copy of. It uses only the Python 3 standard library.

| File | What it does |
|---|---|
| `brother_send.py` | The Brother Wi-Fi protocol (discovery, status, upload), plus a small CLI (`scan`, `info`, `status`, `send`). |
| `stitchsend_core.py` | Higher-level helpers: finding and running Ink/Stitch, reading a design's size from a PES file, saving the machine, checking that a design fits, sending. |

## The protocol in brief

Brother's Wi-Fi embroidery machines run a small HTTPS server on port 443 with a self-signed certificate. There is no pairing and no password. This is the "pedxml" API used by Brother's Windows app, *Design Database Transfer*.

| Request | Purpose |
|---|---|
| `GET /info` | JSON: model, name, firmware, embroidery area (`features.embwidth`/`embheight`, in units of 0.1 mm), and `apis`. A machine is compatible if `apis` contains `pedxml`. |
| `POST /sewing/sewing.cgi` with form body `req_sessionid=0&req_appid=23&req_appver=1.2.0&req_appstate=2` | XML status: total and free design memory, and the files on the machine. The firmware misspells the root element as `<respose_info>`. |
| `POST /sewing/sewing.cgi` as multipart, with a `req_parameter` part (`...&req_appver=100&req_appstate=3`) and a `myfile` part | Uploads a design. The machine answers `204 No Content`. |

Quirks the machine cares about:
- The `User-Agent` must be `Design Database Transfer`.
- The multipart headers are written with no spaces, e.g. `Content-Disposition:form-data;name=...`, exactly as Brother's app sends them.
- The machines don't announce themselves on the network. Discovery means sweeping the local /24 subnet for hosts with port 443 open, then checking each one's `/info`.

### Design size from a PES file

A PES file stores the offset of its PEC block at bytes 8–11 (little-endian). The PEC block starts with `LA:`. The design's width and height are two little-endian 16-bit values, in units of 0.1 mm, located 520 bytes after the start of the PEC block. Byte 48 of the PEC block holds the number of colors minus one.

## Settings

`~/.stitchdrop.json` is shared by every tool:

```json
{ "ip": "192.168.1.50", "name": "SE700", "save_copy": true, "inkstitch_path": "optional override" }
```

## Credits

The protocol details come from [Ember Bridge](https://github.com/EmberSoftwareInc/ember-bridge) (MIT) and [Lilo](https://github.com/Kadwood/lilo) (GPL-3.0). The PES layout follows [pyembroidery](https://github.com/EmbroidePy/pyembroidery).
