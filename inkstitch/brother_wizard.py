"""Two-step GTK window: 1) find the embroidery machine, 2) send the design."""
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

import stitchsend_core as core  # noqa: E402

CSS = b"""
.wiz-title { font-size: 17px; font-weight: bold; }
.wiz-step  { color: alpha(currentColor, 0.6); font-size: 12px; }
.wiz-card  { border: 1px solid alpha(currentColor, 0.18); border-radius: 10px; padding: 12px 14px; }
.wiz-big   { font-size: 15px; font-weight: bold; }
.wiz-dim   { color: alpha(currentColor, 0.65); }
.wiz-ok    { color: #2f7d5b; }
.wiz-bad   { color: #b8412e; }
"""


def in_thread(work, done):
    """Run work() off the UI thread, then done(result, error) on the UI thread."""
    def runner():
        try:
            result, error = work(), None
        except core.UserError as e:
            result, error = None, str(e)
        except Exception as e:  # unexpected: still show something readable
            result, error = None, f"Something went wrong: {e}"
        GLib.idle_add(lambda: (done(result, error), False)[1])
    threading.Thread(target=runner, daemon=True).start()


def label(text="", css=None, wrap=True, xalign=0.0, markup=False):
    lbl = Gtk.Label()
    lbl.set_markup(text) if markup else lbl.set_text(text)
    lbl.set_xalign(xalign)
    lbl.set_line_wrap(wrap)
    lbl.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    lbl.set_max_width_chars(60)
    for c in (css or "").split():
        lbl.get_style_context().add_class(c)
    return lbl


def esc(s):
    return GLib.markup_escape_text(str(s))


class Wizard(Gtk.Window):
    def __init__(self, svg_path, selected_ids):
        super().__init__(title="Send to Brother Machine")
        self.svg_path = svg_path
        self.selected_ids = list(selected_ids)
        self.real_path, self.design_name = core.document_info(svg_path)
        self.machine = None
        self.found = []
        self.pes = None
        self.facts = None
        self.export_error = None
        self.export_token = 0
        self.busy = False

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.set_default_size(520, -1)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.connect("destroy", Gtk.main_quit)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, border_width=20)
        self.add(outer)
        self.step_lbl = label(css="wiz-step")
        self.title_lbl = label(css="wiz-title")
        outer.pack_start(self.step_lbl, False, False, 0)
        outer.pack_start(self.title_lbl, False, False, 0)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_homogeneous(False)
        self.stack.set_vhomogeneous(False)
        outer.pack_start(self.stack, True, True, 0)
        self.stack.add_named(self.build_find_page(), "find")
        self.stack.add_named(self.build_send_page(), "send")
        self.stack.add_named(self.build_done_page(), "done")

        buttons = Gtk.Box(spacing=8)
        outer.pack_end(buttons, False, False, 0)
        self.back_btn = Gtk.Button(label="← Back")
        self.back_btn.connect("clicked", lambda *_: self.go_find())
        self.cancel_btn = Gtk.Button(label="Cancel")
        self.cancel_btn.connect("clicked", lambda *_: self.destroy())
        self.next_btn = Gtk.Button()
        self.next_btn.get_style_context().add_class("suggested-action")
        self.next_btn.connect("clicked", self.on_next)
        buttons.pack_start(self.back_btn, False, False, 0)
        buttons.pack_end(self.next_btn, False, False, 0)
        buttons.pack_end(self.cancel_btn, False, False, 0)
        outer.pack_end(Gtk.Separator(), False, False, 0)

        self.show_all()
        self.start_export()
        self.go_find()
        self.auto_find()
        self.present()

    # ------------------------------------------------------------ page 1: find
    def build_find_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        status = Gtk.Box(spacing=8)
        self.find_spinner = Gtk.Spinner()
        self.find_status = label()
        status.pack_start(self.find_spinner, False, False, 0)
        status.pack_start(self.find_status, True, True, 0)
        box.pack_start(status, False, False, 0)

        self.machine_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.machine_list.get_style_context().add_class("wiz-card")
        self.machine_list.connect("row-selected", self.on_machine_selected)
        box.pack_start(self.machine_list, False, False, 0)

        actions = Gtk.Box(spacing=8)
        self.scan_btn = Gtk.Button(label="Search network again")
        self.scan_btn.connect("clicked", lambda *_: self.do_scan())
        actions.pack_start(self.scan_btn, False, False, 0)
        box.pack_start(actions, False, False, 0)

        manual = Gtk.Expander(label="Enter the machine's IP address instead")
        mbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6)
        row = Gtk.Box(spacing=8)
        self.ip_entry = Gtk.Entry(placeholder_text="e.g. 192.168.1.50")
        self.ip_entry.connect("activate", lambda *_: self.do_connect_ip())
        self.ip_btn = Gtk.Button(label="Connect")
        self.ip_btn.connect("clicked", lambda *_: self.do_connect_ip())
        row.pack_start(self.ip_entry, True, True, 0)
        row.pack_start(self.ip_btn, False, False, 0)
        mbox.pack_start(row, False, False, 0)
        mbox.pack_start(label("The machine shows its IP under Settings → Wireless LAN.", "wiz-dim"), False, False, 0)
        manual.add(mbox)
        box.pack_start(manual, False, False, 0)
        return box

    def set_find_status(self, text, spinning=False, css=None):
        self.find_status.set_text(text)
        ctx = self.find_status.get_style_context()
        for c in ("wiz-ok", "wiz-bad"):
            ctx.remove_class(c)
        if css:
            ctx.add_class(css)
        self.find_spinner.start() if spinning else self.find_spinner.stop()
        self.find_spinner.set_visible(spinning)

    def set_find_busy(self, busy):
        self.busy = busy
        for w in (self.scan_btn, self.ip_btn, self.ip_entry):
            w.set_sensitive(not busy)
        self.update_buttons()

    def show_machines(self, machines, saved_ip=None):
        self.found = machines
        for child in self.machine_list.get_children():
            self.machine_list.remove(child)
        for m in machines:
            row = Gtk.ListBoxRow()
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin=6)
            tag = "  · saved" if m["ip"] == saved_ip else ""
            v.pack_start(label(f"{esc(m['name'])}<span size='small' alpha='60%'>{tag}</span>",
                               "wiz-big", markup=True), False, False, 0)
            v.pack_start(label(machine_line(m), "wiz-dim"), False, False, 0)
            row.add(v)
            self.machine_list.add(row)
        self.machine_list.show_all()
        self.machine_list.set_visible(bool(machines))   # after show_all, which would re-show it
        if machines:
            self.machine_list.select_row(self.machine_list.get_row_at_index(0))
        else:
            self.machine = None
        self.update_buttons()

    def on_machine_selected(self, _box, row):
        self.machine = self.found[row.get_index()] if row is not None else None
        self.update_buttons()

    def auto_find(self):
        saved = core.load_cfg().get("ip")
        if not saved:
            self.do_scan()
            return
        self.set_find_busy(True)
        self.set_find_status(f"Checking your saved machine at {saved}…", spinning=True)

        def done(machine, error):
            self.set_find_busy(False)
            if machine:
                self.set_find_status("Found your saved machine.", css="wiz-ok")
                self.show_machines([machine], saved_ip=saved)
            else:
                self.set_find_status(f"Your saved machine at {saved} didn't answer. Searching the network…")
                self.do_scan(saved_ip=saved)
        in_thread(lambda: core.probe(saved), done)

    def do_scan(self, saved_ip=None):
        self.show_machines([])
        self.set_find_busy(True)
        self.set_find_status("Searching your Wi-Fi network for Brother machines…", spinning=True)

        def progress(done, total):
            GLib.idle_add(lambda: (self.set_find_status(
                f"Searching your Wi-Fi network… {100 * done // max(total, 1)}%", spinning=True), False)[1])

        def done(machines, error):
            self.set_find_busy(False)
            if error:
                self.set_find_status(error, css="wiz-bad")
            elif machines:
                n = len(machines)
                self.set_find_status("Found 1 machine." if n == 1 else f"Found {n} machines. Pick one.",
                                     css="wiz-ok")
                self.show_machines(machines, saved_ip=saved_ip or core.load_cfg().get("ip"))
            else:
                self.set_find_status("No Brother machine found.\n" + core.NOT_FOUND_HELP, css="wiz-bad")
        in_thread(lambda: core.scan_network(progress), done)

    def do_connect_ip(self):
        ip = self.ip_entry.get_text().strip()
        if not ip:
            return
        self.set_find_busy(True)
        self.set_find_status(f"Connecting to {ip}…", spinning=True)

        def done(machine, error):
            self.set_find_busy(False)
            if machine:
                self.set_find_status(f"Found a machine at {ip}.", css="wiz-ok")
                self.show_machines([machine], saved_ip=core.load_cfg().get("ip"))
            else:
                self.set_find_status(f"No Brother machine answered at {ip}.", css="wiz-bad")
        in_thread(lambda: core.probe(ip), done)

    # ------------------------------------------------------------ page 2: send
    def build_send_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.to_lbl = label(css="wiz-dim")
        box.pack_start(self.to_lbl, False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.get_style_context().add_class("wiz-card")
        self.design_lbl = label(css="wiz-big")
        status = Gtk.Box(spacing=8)
        self.export_spinner = Gtk.Spinner()
        self.design_facts = label(css="wiz-dim")
        status.pack_start(self.export_spinner, False, False, 0)
        status.pack_start(self.design_facts, True, True, 0)
        self.check_lbl = label()
        card.pack_start(self.design_lbl, False, False, 0)
        card.pack_start(status, False, False, 0)
        card.pack_start(self.check_lbl, False, False, 4)
        box.pack_start(card, False, False, 0)

        self.selected_chk = Gtk.CheckButton(label=f"Only the selected objects ({len(self.selected_ids)})")
        self.selected_chk.connect("toggled", lambda *_: self.start_export())
        self.selected_chk.set_no_show_all(not self.selected_ids)
        box.pack_start(self.selected_chk, False, False, 0)

        self.copy_chk = Gtk.CheckButton(label="Also save a .pes copy next to my SVG")
        self.copy_chk.set_active(core.load_cfg().get("save_copy", True))
        box.pack_start(self.copy_chk, False, False, 0)

        self.send_error = label(css="wiz-bad")
        self.send_error.set_no_show_all(True)
        box.pack_start(self.send_error, False, False, 0)
        return box

    def start_export(self):
        self.export_token += 1
        token = self.export_token
        self.pes, self.facts, self.export_error = None, None, None
        ids = self.selected_ids if self.selected_chk.get_active() else []
        self.refresh_send_page()

        def done(pes, error):
            if token != self.export_token:      # a newer export replaced this one
                return
            self.pes, self.export_error = pes, error
            self.facts = core.pes_facts(pes) if pes else None
            self.refresh_send_page()
        in_thread(lambda: core.export_pes(self.svg_path, ids), done)

    def refresh_send_page(self):
        self.design_lbl.set_text(f"“{self.design_name}”")
        if self.machine:
            self.to_lbl.set_markup(f"To <b>{esc(self.machine['name'])}</b> at {esc(self.machine['ip'])}")
        ctx = self.check_lbl.get_style_context()
        for c in ("wiz-ok", "wiz-bad"):
            ctx.remove_class(c)
        if self.export_error:
            self.export_spinner.stop()
            self.export_spinner.hide()
            self.design_facts.hide()
            self.check_lbl.set_text(self.export_error)
            ctx.add_class("wiz-bad")
        elif self.pes is None:
            self.export_spinner.show()
            self.export_spinner.start()
            self.design_facts.show()
            self.design_facts.set_text("Generating stitches with Ink/Stitch…")
            self.check_lbl.set_text("")
        else:
            self.export_spinner.stop()
            self.export_spinner.hide()
            self.design_facts.show()
            self.design_facts.set_text(facts_line(self.facts))
            problem = core.fit_problem(self.facts, self.machine) if self.machine else None
            if problem:
                self.check_lbl.set_text("✗ " + problem)
                ctx.add_class("wiz-bad")
            elif self.machine and "area_mm" in self.machine:
                a = self.machine["area_mm"]
                self.check_lbl.set_text(f"✓ Fits the {a[0]:.0f} × {a[1]:.0f} mm embroidery area")
                ctx.add_class("wiz-ok")
            else:
                self.check_lbl.set_text("")
        self.update_buttons()

    def do_send(self):
        self.busy = True
        self.send_error.hide()
        self.update_buttons()
        self.next_btn.set_label("Sending…")
        save = self.copy_chk.get_active()
        core.save_cfg({"save_copy": save})
        machine, name, pes = self.machine, self.design_name, self.pes

        def work():
            core.send(machine, name, pes)
            copy_path, copy_err = None, None
            if save:
                try:
                    copy_path = core.save_copy(self.real_path, name, pes)
                except OSError as e:
                    copy_err = str(e)
            return copy_path, copy_err

        def done(result, error):
            self.busy = False
            if error:
                self.send_error.set_text(error)
                self.send_error.show()
                self.update_buttons()
                return
            self.go_done(*result)
        in_thread(work, done)

    # ------------------------------------------------------------ page 3: done
    def build_done_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.done_main = label(css="wiz-big wiz-ok")
        self.done_detail = label(css="wiz-dim")
        box.pack_start(self.done_main, False, False, 0)
        box.pack_start(self.done_detail, False, False, 0)
        return box

    # ------------------------------------------------------------ navigation
    def go_find(self):
        self.page = "find"
        self.stack.set_visible_child_name("find")
        self.step_lbl.set_text("STEP 1 OF 2")
        self.title_lbl.set_text("Find your embroidery machine")
        self.update_buttons()

    def go_send(self):
        core.remember_machine(self.machine)      # step 1 confirmed → saved
        self.page = "send"
        self.stack.set_visible_child_name("send")
        self.step_lbl.set_text("STEP 2 OF 2")
        self.title_lbl.set_text("Send your design")
        self.refresh_send_page()

    def go_done(self, copy_path, copy_err):
        self.page = "done"
        self.stack.set_visible_child_name("done")
        self.step_lbl.set_text("DONE")
        self.title_lbl.set_text("Design sent")
        self.done_main.set_text(f"✓ “{self.design_name}” is on {self.machine['name']}")
        detail = "On the machine, open the embroidery screen and choose the received design."
        if copy_path:
            detail += f"\n\nA copy was saved to {copy_path}"
        elif copy_err:
            detail += f"\n\n(Couldn't save a copy: {copy_err})"
        self.done_detail.set_text(detail)
        self.update_buttons()

    def on_next(self, *_):
        if self.page == "find":
            self.go_send()
        elif self.page == "send":
            self.do_send()
        else:
            self.destroy()

    def update_buttons(self):
        page = getattr(self, "page", "find")
        self.back_btn.set_visible(page == "send")
        self.back_btn.set_sensitive(not self.busy)
        self.cancel_btn.set_visible(page != "done")
        if page == "find":
            self.next_btn.set_label("Next →")
            self.next_btn.set_sensitive(self.machine is not None and not self.busy)
        elif page == "send":
            ready = (self.pes is not None and not self.export_error and not self.busy
                     and not core.fit_problem(self.facts, self.machine))
            if not self.busy:
                self.next_btn.set_label("Send to machine")
            self.next_btn.set_sensitive(ready)
        else:
            self.next_btn.set_label("Done")
            self.next_btn.set_sensitive(True)


def machine_line(m):
    bits = [m["ip"]]
    if "area_mm" in m:
        bits.append(f"{m['area_mm'][0]:.0f} × {m['area_mm'][1]:.0f} mm area")
    if "free_kb" in m:
        bits.append(f"{m['free_kb']} KB free")
    if m.get("firmware"):
        bits.append(f"firmware {m['firmware']}")
    return " · ".join(bits)


def facts_line(f):
    bits = []
    if "width_mm" in f:
        bits.append(f"{f['width_mm']:.0f} × {f['height_mm']:.0f} mm")
    if "colors" in f:
        bits.append(f"{f['colors']} color{'s' if f['colors'] != 1 else ''}")
    bits.append(f"{f['kb']:.1f} KB")
    return " · ".join(bits)


def run(svg_path, selected_ids=()):
    Wizard(svg_path, selected_ids)
    Gtk.main()
