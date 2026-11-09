"""Lexer/parser (spec 11.2 step 1-2): reuses the validator's port of oef2wims process()
(validation/oef/oef_validate/oef_validate.py, loaded unmodified: REQ-ARCH-5).

Produces the OEF AST: top-level directives with raw parameter text and source positions,
nested into if/ifval/for/while bodies. Nothing is interpreted here (REQ-ARCH, 11.2 step 2).
"""
from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .decode import line_col, normalise

_VALIDATOR = None


def _find_validator_dir() -> Path:
    env = os.environ.get("OEF2XML_VALIDATE_DIR")
    cands = []
    if env:
        cands.append(Path(env))
    here = Path(__file__).resolve()
    for up in (2, 3):  # src/oef2xml/parser.py -> repo root is parents[2]
        if len(here.parents) > up:
            cands.append(here.parents[up] / "validation" / "oef" / "oef_validate")
    for c in cands:
        if (c / "oef_validate.py").is_file() and (c / "oef_spec.json").is_file():
            return c
    raise RuntimeError("oef_validate.py not found; set OEF2XML_VALIDATE_DIR (REQ-ARCH-5 keeps validation/ in place)")


def validator_module():
    global _VALIDATOR
    if _VALIDATOR is None:
        d = _find_validator_dir()
        spec = importlib.util.spec_from_file_location("oef_validate_shared", d / "oef_validate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with open(d / "oef_spec.json", encoding="utf-8") as f:
            mod._SPEC = json.load(f)
        _VALIDATOR = mod
    return _VALIDATOR


@dataclass
class Directive:
    name: str
    pos: int
    vals: list[str]
    arg_starts: list[int]          # absolute offset of each raw parameter
    end: int                       # offset just after the directive header (last parameter)
    post: bool                     # defined after \statement (post-definition, 7.1)
    line: int = 0
    col: int = 0

    def raw_text(self, text: str) -> str:
        return text[self.pos:self.end]


@dataclass
class Block:
    """if/ifval/for/while with body. kind in {if, ifval, for, while}."""
    kind: str
    head: Directive
    body: list = field(default_factory=list)
    orelse: list = field(default_factory=list)
    has_else: bool = False
    end: int = 0                   # offset just after the closing brace of the (last) body


@dataclass
class ParseResult:
    text: str
    items: list                    # Directive | Block, in source order
    directives: list[Directive]    # every real directive (flat, including those inside bodies)
    errors: list[tuple[int, str]]  # (pos, message) -> echec
    warnings: list[tuple[int, str, str]]  # (pos, code, message)
    n_directives: int = 0


CTRL_NAMES = {"else", "endif", "next", "endwhile"}


def parse(text: str, strict_limits: bool = False) -> ParseResult:
    """REQ-IN-2/5. `text` is decoded text (any line endings)."""
    v = validator_module()
    lim = v._SPEC["limits"]
    errors: list[tuple[int, str]] = []
    warnings: list[tuple[int, str, str]] = []
    nbytes = len(text.encode("utf-8"))
    if len(text) == 0:
        errors.append((0, "Empty source file."))
        return ParseResult(text, [], [], errors, warnings)
    b = list(normalise(text))
    val = v.Validator(v._SPEC)
    val.text = "".join(b)
    bad = val.check_parentheses(b)
    if bad:
        errors.append((bad[0], f"Unmatched parentheses '{bad[1]}'"))
        return ParseResult(text, [], [], errors, warnings)
    issues: list = []

    def add(level, pos, msg):
        issues.append((level, pos, msg))

    # the validator copies the whole buffer; process() mutates b in place
    defs = val.process(b, add)
    for level, pos, msg in issues:
        if level == "erreur":
            if "MAX_DEFINE" in msg:
                if strict_limits:
                    errors.append((pos, "LIMIT-1024: " + msg))
                else:
                    warnings.append((pos, "LIMIT-1024", msg))
            else:
                errors.append((pos, msg))
        else:
            warnings.append((pos, "WARN", msg))
    if defs is None:
        return ParseResult(text, [], [], errors, warnings)
    flat: list[Directive] = []
    items: list = []
    cur = items
    cur_stack: list = []
    for d in defs:
        name = d["name"]
        if "vals" not in d:  # control pseudo-directive
            if name == "else" and cur_stack:
                blk = cur_stack[-1]
                blk.has_else = True
                cur = blk.orelse
            elif name in ("endif", "next", "endwhile") and cur_stack:
                cur_stack[-1].end = d["pos"] + 1
                cur_stack.pop()
                cur = _current_list(cur_stack, items)
            continue
        line, col = line_col(text, d["pos"])
        dr = Directive(name, d["pos"], list(d["vals"]), [s for s, _ in d["args"]],
                       (d["args"][-1][1] + 1) if d["args"] else d["pos"] + 1 + len(name),
                       bool(d["post"]), line, col)
        flat.append(dr)
        if name in ("if", "ifval", "for", "while"):
            blk = Block(name, dr)
            cur.append(blk)
            cur_stack.append(blk)
            cur = blk.body
        else:
            cur.append(dr)
    # unterminated control blocks cannot happen after parentheses check; ignore
    return ParseResult(text, items, flat, errors, warnings, len(flat))


def _current_list(cur_stack, items):
    if not cur_stack:
        return items
    blk = cur_stack[-1]
    return blk.orelse if blk.has_else else blk.body
