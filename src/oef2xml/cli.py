"""Command line (12.1), batch behaviour (12.2), Unicode paths (12.3)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from . import __version__
from . import report as R
from .blocks import to_dict
from .convert import Options, convert_bytes
from .pipeline import Config, process_bytes

EXIT_USAGE = 64


class Usage(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):            # REQ-REP-6: exit code 64 on bad usage
        self.print_usage(sys.stderr)
        sys.stderr.write(f"oef2xml: error: {message}\n")
        sys.exit(EXIT_USAGE)


def fs(p) -> str:
    """REQ-WIN-1: `\\\\?\\` prefix for long paths on Windows (LongPathsEnabled=0); identity elsewhere"""
    s = str(p)
    if os.name == "nt" and len(s) >= 240 and not s.startswith("\\\\?\\"):
        s = "\\\\?\\" + os.path.abspath(s)
    return s


def build_parser() -> Parser:
    p = Parser(prog="oef2xml", description="Convert WIMS OEF files into XML programs (urn:eleda:program:v1).")
    p.add_argument("inputs", nargs="*", metavar="INPUT", help=".oef file or directory")
    p.add_argument("-o", "--out", default="./oef2xml_out", help="output folder (default ./oef2xml_out)")
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument("--report", metavar="FILE.json")
    p.add_argument("--csv", metavar="FILE.tsv")
    p.add_argument("--encoding", default="auto", choices=["auto", "utf-8", "latin-1", "cp1252"])
    p.add_argument("--default-lang", default="fr", choices=["fr", "en", "es", "it", "de", "ar"])
    p.add_argument("--max-attempts", type=int, default=1)
    p.add_argument("--source-format", default="ir", choices=["ir", "json", "yaml", "xml"])
    p.add_argument("--id-from", default="stem", choices=["stem", "hash"])
    p.add_argument("--gate", default="auto", choices=["auto", "oef2wims", "validator", "none"])
    p.add_argument("--oef2wims", metavar="PATH")
    p.add_argument("--def", dest="def_path", metavar="FILE|DIR", help="accepted; cross-check with .def files is phase 2")
    p.add_argument("--validate", default="rng,xsd", help="rng,xsd,sch|none (default rng,xsd)")
    p.add_argument("--schema-dir", metavar="DIR")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--html", default="pass", choices=["pass", "strict"])
    p.add_argument("--trig-units", choices=["deg", "rad"], default=None,
                   help="no default: without it trigonometry is a gap G-21 (REQ-EXPR-4)")
    p.add_argument("--strict-limits", action="store_true")
    p.add_argument("--placeholder-carrier", default="text", choices=["text", "display_element"])
    p.add_argument("--idioms", default="on", choices=["on", "off"])
    p.add_argument("--schematron", metavar="FILE")
    p.add_argument("--keep-gate-files", metavar="DIR", nargs="?", const="oef2xml_gate_files")
    p.add_argument("--mdef", metavar="NAME[,NAME]", help="accepted; \\mdef is a gap (G-14)")
    p.add_argument("--assets-dir", metavar="DIR", help="accepted; image copying is phase 2 (M-47)")
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--dump", action="store_true", help="pseudo-code of one file")
    p.add_argument("--dump-ir", action="store_true", help="IR JSON of one file")
    p.add_argument("--suffix", default="", help="suffix of the output stem, e.g. _OEF2XML_v1")
    p.add_argument("--force", action="store_true", help="allow writing into an input folder")
    p.add_argument("--fail-fast", action="store_true")
    p.add_argument("--no-check-placeholders", action="store_true")
    p.add_argument("--stamp", action="store_true", help="emit createdAt/updatedAt (Q9)")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version=f"oef2xml {__version__}")
    return p


def collect(inputs, recursive: bool) -> list[Path]:
    files: list[Path] = []
    for i in inputs:
        pth = Path(i)
        if pth.is_dir():
            it = pth.rglob("*") if recursive else pth.glob("*")
            files += [f for f in it if f.is_file() and f.suffix.lower() == ".oef"]
        elif pth.is_file():
            files.append(pth)
        else:
            raise Usage(f"input not found: {i}")
    uniq = {}
    for f in files:
        uniq[os.path.abspath(f)] = f
    return [uniq[k] for k in sorted(uniq)]


def options_from(a) -> Options:
    return Options(encoding=a.encoding, default_lang=a.default_lang, max_attempts=a.max_attempts, source_format=a.source_format,
                   id_from=a.id_from, trig_units=a.trig_units, html=a.html, strict=a.strict, strict_limits=a.strict_limits,
                   carrier=a.placeholder_carrier, idioms=(a.idioms == "on"), stamp=a.stamp)


def _work(args):
    path, name, opts, cfg, stem = args
    try:
        raw = Path(fs(path)).read_bytes()
    except OSError as ex:
        entry, xml = process_bytes(str(path), b"", opts, cfg, stem)
        entry["message"] = f"unreadable file: {ex}"
        entry["details"] = [{"niveau": "erreur", "ligne_oef": 0, "colonne_oef": 0, "construct": "io", "regle": "REQ-IN-5", "message": entry["message"]}]
        return entry, None
    try:
        return process_bytes(str(path), raw, opts, cfg, stem)
    except Exception as ex:          # REQ-BATCH-1: never a lost entry
        entry, _ = process_bytes(str(path), b"", opts, cfg, stem)
        entry.update(statut="echec", message=f"internal error: {type(ex).__name__}: {ex}")
        entry["flags"] = ["crash"]
        entry["details"] = [{"niveau": "erreur", "ligne_oef": 0, "colonne_oef": 0, "construct": "crash", "regle": "REQ-BATCH-1", "message": entry["message"]}]
        return entry, None


def render_dump(b, indent=0, out=None):
    out = [] if out is None else out
    pad = "  " * indent
    while b is not None:
        fl = " ".join(f"{n}={t!r}" if v is None else f"{n}=${v}" for n, t, v, _ in b.fields)
        out.append(f"{pad}{b.type} {fl}  [{b.rule}]")
        for n, sub, _ in b.inputs:
            if sub is not None:
                out.append(f"{pad}  .{n}:")
                render_dump(sub, indent + 2, out)
        b = b.next
    return out


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    os.environ.setdefault("PYTHONUTF8", "1")
    a = build_parser().parse_args(argv)
    try:
        if not a.inputs:
            raise Usage("no input")
        if a.max_attempts < 0:
            raise Usage("--max-attempts must be >= 0")
        files = collect(a.inputs, a.recursive)
        if not files:
            raise Usage("no .oef file found")
        opts = options_from(a)
        if a.dump or a.dump_ir:
            if len(files) != 1:
                raise Usage("--dump/--dump-ir work on exactly one file")
            res = convert_bytes(str(files[0]), Path(fs(files[0])).read_bytes(), opts)
            if res.errors:
                print("\n".join(res.errors), file=sys.stderr)
                return 2
            if a.dump_ir:
                print(json.dumps({"id": res.program.prog_id, "status": res.status, "counters": res.counters,
                                  "chain": to_dict(res.program.chain),
                                  "placeholders": [{"rule": p.rule, "construct": p.construct, "reason": p.reason, "raw": p.raw}
                                                   for p in res.program.placeholders]}, ensure_ascii=False, indent=1))
            else:
                print("\n".join(render_dump(res.program.chain)))
            return 0
        out = Path(a.out)
        in_dirs = {os.path.realpath(f.parent) for f in files}
        if os.path.realpath(out) in in_dirs and not a.force:
            raise Usage(f"refusing to write into the input folder {out} (REQ-BATCH-2); use --force or another --out")
        vparts = [x.strip() for x in a.validate.split(",") if x.strip()]
        if a.validate.strip() != "none" and not set(vparts) <= {"rng", "xsd", "sch"}:
            raise Usage("--validate expects rng,xsd,sch or none")
        cfg = Config(gate=a.gate, oef2wims=a.oef2wims, validate=(a.validate.strip() != "none"), schema_dir=a.schema_dir,
                     strict=a.strict, keep_gate_files=a.keep_gate_files, check_placeholders=not a.no_check_placeholders)
        # deterministic output names (collisions get _2, _3 ... in sorted order)
        names, seen = [], {}
        for f in files:
            stem = f.stem
            n = seen.get(stem, 0) + 1
            seen[stem] = n
            names.append(stem if n == 1 else f"{stem}_{n}")
    except Usage as ex:
        print(f"oef2xml: {ex}", file=sys.stderr)
        return EXIT_USAGE
    except FileNotFoundError as ex:
        print(f"oef2xml: {ex}", file=sys.stderr)
        return EXIT_USAGE
    if a.assets_dir or a.def_path or a.mdef:
        print("oef2xml: --assets-dir/--def/--mdef are accepted but not used in this phase", file=sys.stderr)
    jobs = [(f, f.name, opts, cfg, st) for f, st in zip(files, names)]
    entries: list[dict] = []
    try:
        if a.jobs > 1 and not a.fail_fast:
            with ProcessPoolExecutor(max_workers=a.jobs) as ex:
                results = list(ex.map(_work, jobs, chunksize=8))
        else:
            results = []
            for j in jobs:
                r = _work(j)
                results.append(r)
                if a.fail_fast and r[0]["statut"] == "echec":
                    break
    except FileNotFoundError as ex:
        print(f"oef2xml: {ex}", file=sys.stderr)
        return EXIT_USAGE
    out.mkdir(parents=True, exist_ok=True)
    for (f, _, _, _, stem), (entry, xml) in zip(jobs, results):
        if xml is not None:
            target = out / f"{stem}{a.suffix}.xml"
            Path(fs(target)).write_bytes(xml)
            entry["sortie"] = target.name          # relative to --out: reports stay byte-identical across output folders (AC-6)
        check = out / f"{stem}.check"
        lines = [f"statut: {entry['statut']}", f"compilateur: {entry['compilateur']}", f"rng: {entry['rng']}", f"xsd: {entry['xsd']}"]
        if entry["message"]:
            lines.append("message: " + entry["message"])
        Path(fs(check)).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        entries.append(entry)
        if a.verbose and not a.quiet:
            print(f"{entry['statut']:8s} {entry['source']}")
    if a.report:
        R.write_json(fs(a.report), entries)
    if a.csv:
        R.write_tsv(fs(a.csv), entries)
    if not a.quiet:
        s = R.summarize(entries)["resume"]
        print(f"oef2xml {__version__}: {s['fichiers']} file(s): {s['complet']} complet, {s['partiel']} partiel, {s['echec']} echec")
    return R.exit_code(entries)


if __name__ == "__main__":
    sys.exit(main())
