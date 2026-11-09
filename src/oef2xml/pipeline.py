"""One file through the whole pipeline (11.2): decode -> parse -> semantic pass -> gate -> emit -> validate.
Returns a report entry (REQ-REP-2) and the XML bytes (None for echec)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from . import validate as V
from .convert import Options, Result, convert_bytes
from .decode import line_col
from .emit import Emitter
from .gate import find_oef2wims, run_gate

ZERO = {"questions_source": 0, "questions_converties": 0, "questions_gap": 0, "questions_taint": 0,
        "blocs_question_emis": 0, "directives_source": 0, "directives_traduites": 0, "directives_approximees": 0,
        "directives_info": 0, "directives_non_traduites": 0}


@dataclass
class Config:
    gate: str = "auto"                  # auto|oef2wims|validator|none
    oef2wims: str | None = None
    validate: bool = True               # rng + xsd
    schema_dir: str | None = None
    strict: bool = False
    keep_gate_files: str | None = None
    check_placeholders: bool = True
    source_name: str = ""               # shown in placeholders (file name)


def resolve_gate(cfg: Config) -> tuple[str, str | None]:
    if cfg.gate == "none":
        return "none", None
    if cfg.gate in ("auto", "oef2wims"):
        exe = find_oef2wims(cfg.oef2wims)
        if exe:
            return "oef2wims", exe
        if cfg.gate == "oef2wims":
            raise FileNotFoundError("oef2wims not found: use --oef2wims PATH or $OEF2XML_OEF2WIMS")
    return "validator", None


def process_bytes(path: str, raw: bytes, opts: Options, cfg: Config, stem: str | None = None):
    """-> (entry dict, xml bytes | None)"""
    gate_mode, exe = resolve_gate(cfg)
    res = convert_bytes(path, raw, opts)
    msgs: list[str] = []
    flags = list(res.flags)
    compilateur = "non_execute"
    if gate_mode == "oef2wims":
        g = run_gate(exe, stem or Path(path).stem, raw, cfg.keep_gate_files)
        if g.ok:
            compilateur = "ok"
            if res.errors and not any(e.startswith("internal error") for e in res.errors) and res.nbytes:
                flags.append("divergence_parser_compilateur")
        else:
            compilateur = "ko"
            cmsg = f"{g.message} at line {g.line} col {g.col}." if g.line else g.message
            parser_msgs = [e for e in res.errors if e != cmsg]
            if not res.errors or all(e.startswith("internal error") for e in res.errors):
                flags.append("divergence_parser_compilateur")
            res.errors = [f"compilateur: {cmsg}"] + [f"analyseur: {e}" for e in parser_msgs]
    elif gate_mode == "validator":
        compilateur = "ko" if res.errors else "ok"
    xml = None
    rng = xsd = "non_execute"
    status = res.status
    if res.errors:
        status = "echec"
    else:
        schema_dir = cfg.schema_dir or str(V.default_schema_dir())
        prog = res.program
        em = Emitter(prog, cfg.source_name or Path(path).name, lambda p: line_col(res.text, p), opts.carrier, opts.source_format, opts.stamp)
        xml = em.build()
        if cfg.validate:
            ok_r, ok_x, vm = V.validate_rng_xsd(xml, schema_dir)
            rng, xsd = ("ok" if ok_r else "ko"), ("ok" if ok_x else "ko")
            if not (ok_r and ok_x):
                res.errors.append("internal error: output not valid: " + "; ".join(vm))
        lint = V.shape_lint(xml, schema_dir)
        if lint:
            res.errors.append("internal error: shape lint: " + "; ".join(lint[:3]))
        scanned = V.count_question_blocks(xml)
        if scanned != res.counters["blocs_question_emis"]:
            res.errors.append(f"internal error: I3 violated (XML scan {scanned} != counter {res.counters['blocs_question_emis']})")
        if cfg.check_placeholders:
            pl = V.placeholder_lint(xml, len(res.program.placeholders), status)
            if pl:
                res.errors.append("internal error: placeholder lint: " + "; ".join(pl[:3]))
        if res.errors:
            status = "echec"
            xml = None
        elif cfg.strict and status == "partiel":
            status = "echec"
            res.errors.append("--strict: partial file refused")
            xml = None
    counters = dict(ZERO)
    if res.counters and status != "echec":
        counters = {k: res.counters[k] for k in ZERO}
    fid = "approchee" if (status != "echec" and not counters["blocs_question_emis"]) else "non_verifiee"
    entry = {
        "source": path,
        "sortie": None,
        "id": res.program.prog_id if res.program else None,
        "titre": res.title,
        "statut": status,
        "fidelite": fid,
        **counters,
        "non_traduits": res.non_traduits if status != "echec" else {},
        "approximations": res.approximations if status != "echec" else {},
        "gaps": res.gaps if status != "echec" else {},
        "flags": sorted(set(flags)),
        "encodage": res.encoding,
        "octets": res.nbytes,
        "compilateur": compilateur,
        "rng": rng,
        "xsd": xsd,
        "schematron": "non_execute",
        "message": "; ".join(res.errors),
        "avertissements": [f"{c}: {m}" for c, m in res.warnings] if res.warnings else [],
        "details": [d.as_dict() for d in res.details] if status != "echec" else [
            {"niveau": "erreur", "ligne_oef": 0, "colonne_oef": 0, "construct": "echec", "regle": "REQ-REP-3", "message": m}
            for m in res.errors],
    }
    return entry, xml
