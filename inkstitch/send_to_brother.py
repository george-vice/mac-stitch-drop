#!/usr/bin/env python3
"""Inkscape extension entry point: Send to Brother Machine (Wi-Fi).

Opens a two-step window: 1) find the embroidery machine, 2) send the design.
Uses the GTK that Inkscape bundles for Python extensions. If GTK isn't
available it falls back to a non-interactive send with a message dialog.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stitchsend_core as core  # noqa: E402


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", action="append", default=[])
    ap.add_argument("svg", nargs="?")
    args, _ = ap.parse_known_args(argv)
    return args


def fallback(args):
    """No GTK: find the machine (saved → scan), then send. Report via stderr."""
    def out(msg):
        sys.stderr.write(msg + "\n")
        sys.exit(0)
    try:
        saved = core.load_cfg().get("ip")
        machine = core.probe(saved) if saved else None
        if not machine:
            found = core.scan_network()
            if not found:
                out("Couldn't find your Brother machine.\n\n" + core.NOT_FOUND_HELP)
            machine = found[0]
        core.remember_machine(machine)
        pes = core.export_pes(args.svg)
        real, name = core.document_info(args.svg)
        facts = core.pes_facts(pes)
        problem = core.fit_problem(facts, machine)
        if problem:
            out(problem)
        core.send(machine, name, pes)
        out(f"✓ Sent “{name}” to {machine['name']} ({machine['ip']}).")
    except core.UserError as e:
        out(str(e))


def main():
    args = parse_args()
    if not args.svg or not os.path.isfile(args.svg):
        sys.stderr.write("Run this from Inkscape: Extensions → Ink/Stitch → Visualize and Export.\n")
        return
    try:
        import brother_wizard
    except Exception:
        fallback(args)
        return
    brother_wizard.run(args.svg, args.id)


if __name__ == "__main__":
    main()
