#!/usr/bin/env python3
"""Round-trip comparison (spec 13.3): O1 --oef2xml--> X1 --xml2oef--> O2 ; normalisation N1-N8 and verdicts
IDENTICAL / DIFF-EXPLAINED / DIFF-SILENT.

N-rules are applied on *directive units* parsed with the converter's own parser, so multi-line statements become one
token stream (N7) and comments are ignored (N2: counted separately). Honesty rule: a difference is DIFF-EXPLAINED only
when the O1 lines of the differing unit contain a reported approximation / gap / G-nn info detail of the same file.
Nothing here is loosened to obtain a pass.

N3 extension (spec silent, P1_QUESTIONS): the forward converter appends `_v` to variable names that start with `x2o`
(XML variable names are kept verbatim by REQ-OUT-7); `\\x2o2` and `\\x2o2_v` are the same temporary.
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from oef2xml import expr as E  # noqa: E402
from oef2xml.decode import decode_bytes, line_col  # noqa: E402
from oef2xml.parser import Block, Directive, parse  # noqa: E402

EXPR_NAMES = {"integer", "int", "real", "rational", "if", "ifval", "while", "for"}
HEADER = {"title", "language", "author", "description"}
TEMP_RE = re.compile(r"(?<![A-Za-z0-9_])(\\?)x2o(rep)?(\d+)(?:_v)?(?![A-Za-z0-9])")


def n6(s: str) -> str:
    return re.sub(r"&#[xX]([0-9a-fA-F]+);", lambda m: f"&#{int(m.group(1), 16)};", s)


OPSYM = {"EQ": "==", "NEQ": "!=", "LT": "<", "LTE": "<=", "GT": ">", "GTE": ">="}


def ast_s(n) -> str:
    """canonical, fully parenthesised text of an expression AST: redundant parentheses and spacing vanish (N5b)"""
    if isinstance(n, E.Num):
        return n.text
    if isinstance(n, E.Var):
        return "\\" + n.name + (f"[{ast_s(n.index)}]" if n.index is not None else "")
    if isinstance(n, E.Const):
        return n.name
    if isinstance(n, E.Un):
        return f"(-{ast_s(n.a)})"
    if isinstance(n, E.Bin):
        return f"({ast_s(n.a)}{n.op}{ast_s(n.b)})"
    if isinstance(n, E.Fn):
        return n.name + "(" + ",".join(ast_s(a) if not isinstance(a, str) else a for a in n.args) + ")"
    if isinstance(n, E.ListLit):
        return "[" + ",".join(re.sub(r"\s+", "", i) for i in n.items) + "]"
    if isinstance(n, E.Str):
        return "".join(p if isinstance(p, str) else ast_s(p) for p in n.parts)
    if isinstance(n, E.Cmp):
        return f"({ast_s(n.a)} {OPSYM[n.op]} {ast_s(n.b)})"
    if isinstance(n, E.Logic):
        return f"({ast_s(n.a)} {n.op.lower()} {ast_s(n.b)})"
    if isinstance(n, E.Not):
        return f"(not {ast_s(n.a)})"
    return repr(n)


def parse_rhs(v: str):
    try:
        return E.parse_expr(v.strip(), set())
    except Exception:
        return None


def int_valued(n, ints) -> bool:
    """value-preserving integer proof used only by N11 (same rules as the converter's)"""
    if isinstance(n, E.Num):
        return re.fullmatch(r"-?\d+", n.text) is not None
    if isinstance(n, E.Var):
        return n.index is None and n.name in ints
    if isinstance(n, E.Un):
        return int_valued(n.a, ints)
    if isinstance(n, E.Bin):
        if n.op in ("+", "-", "*", "%"):
            return int_valued(n.a, ints) and int_valued(n.b, ints)
        return False
    if isinstance(n, E.Fn):
        if n.name in ("randint", "floor", "ceil", "rint", "items"):
            return True
        if n.name == "abs":
            return int_valued(n.args[0], ints)
    return False


def split_def(vals):
    if len(vals) == 1 and "=" in vals[0]:
        a, b = vals[0].split("=", 1)
        return a.strip().lstrip("\\").rstrip(":").strip(), b
    if len(vals) >= 2:
        return vals[0].strip().lstrip("\\"), vals[1]
    return "", ""


def int_names(items) -> set:
    defs: dict = {}

    def walk(its):
        for it in its:
            if isinstance(it, Block):
                walk(it.body)
                walk(it.orelse)
            elif it.name in ("integer", "int", "real", "rational"):
                nm, rhs = split_def(it.vals)
                defs.setdefault(nm, []).append((it.name, parse_rhs(rhs)))
    walk(items)
    # \integer always yields an integer (rint); \real/\rational only when the value is provably integer
    ints = set(defs)
    ch = True
    while ch:
        ch = False
        for n in sorted(ints):
            if any(t not in ("integer", "int") and (nd is None or not int_valued(nd, ints)) for t, nd in defs[n]):
                ints.discard(n)
                ch = True
    return ints


def norm_params(name: str, vals: list[str], ints=frozenset()) -> str:
    if name in ("integer", "int", "real", "rational"):
        nm, rhs = split_def(vals)
        node = parse_rhs(rhs)
        if node is None:
            return "{" + nm + "=" + re.sub(r"\s+", "", rhs) + "}"
        if name in ("integer", "int"):
            if isinstance(node, E.Fn) and node.name == "rint" and len(node.args) == 1:   # N9: \integer is rint(E) (WIMS def.c)
                node = node.args[0]
            tag = "num" if int_valued(node, ints) else "integer"
        else:
            tag = "num" if int_valued(node, ints) else name              # N11
        return "\x00" + tag + "{" + nm + "=" + ast_s(node) + "}"
    if name in ("if", "ifval", "while"):
        try:
            node = E.parse_condition(vals[0], set(), name != "if")
            return "{" + ast_s(node) + "}"
        except Exception:
            return "{" + re.sub(r"\s+", "", vals[0]) + "}"
    out = []
    for v in vals:
        v = v.replace("\r", "")
        if name in EXPR_NAMES:
            v = re.sub(r"\s+", "", v)
        else:
            v = re.sub(r"\s+", " ", v).strip()
            if name == "statement":
                v = re.sub(r"<br\s*/?>", "<br>", v, flags=re.I)
                v = re.sub(r"\s*(<[^>]+>)\s*", r"\1", v)       # N7: whitespace around tags
        out.append(n6(v))
    return "{" + "}{".join(out) + "}"


def cond_numeric_only(vals) -> bool:
    try:
        node = E.parse_condition(vals[0], set(), False)
    except Exception:
        return False
    def only_num(n):
        if isinstance(n, E.Cmp):
            return isinstance(n.a, E.Num) and isinstance(n.b, E.Num)
        if isinstance(n, (E.Logic,)):
            return only_num(n.a) and only_num(n.b)
        if isinstance(n, E.Not):
            return only_num(n.a)
        return False
    return only_num(node)


IDENT_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*")


def strip_forward_suffix(unit: str) -> str:
    """N3 extension: the forward converter appends `_v` to variable names it considers reserved (names starting with
    x2o or already ending in `_v`); the reverse tool keeps names verbatim (REQ-OUT-7)."""
    def fix(m):
        t = m.group(0)
        if t.endswith("_v") and (t[:-2].startswith("x2o") or t[:-2].endswith("_v")):
            return t[:-2]
        return t
    return IDENT_RE.sub(fix, unit)


def norm_item(it, ints=frozenset()):
    if isinstance(it, Block):
        kind = it.kind
        if kind == "if" and cond_numeric_only(it.head.vals[:1]):     # N10: \if{1=0} == \ifval{1==0} on numeric literals
            kind = "ifval"
        head = f"\\{kind}" + norm_params(it.kind if kind == it.kind else "ifval", it.head.vals[:1], ints)
        body = " ".join(norm_item(c, ints) for c in it.body)
        s = head + "[" + body + "]"
        if it.has_else:
            s += "else[" + " ".join(norm_item(c, ints) for c in it.orelse) + "]"
        return s
    p = norm_params(it.name, it.vals, ints)
    if p.startswith("\x00"):          # definitions: the type tag replaces the directive name (N11)
        return "\\" + p[1:]
    return f"\\{it.name}" + p


def spans(it, text):
    if isinstance(it, Block):
        a = it.head.pos
        b = it.end if it.end > 0 else it.head.end
    else:
        a, b = it.pos, it.end
    return line_col(text, a)[0], line_col(text, max(a, b - 1))[0]


def units(text: str):
    """-> (list of (normalised unit, first line, last line), n_marker_lines, n_approx_marker_lines)"""
    pr = parse(text)
    if pr.errors:
        return None, 0, 0
    us = []
    ints = int_names(pr.items)
    for it in pr.items:
        l0, l1 = spans(it, text)
        name = it.kind if isinstance(it, Block) else it.name
        us.append([strip_forward_suffix(norm_item(it, ints)), l0, l1, name])
    head = sorted([u for u in us if u[3] in HEADER], key=lambda u: u[3])
    rest = [u for u in us if u[3] not in HEADER]
    us = head + rest
    # N3: temporaries renamed in order of first occurrence
    names: dict = {}

    def ren(m):
        key = (m.group(2) or "", m.group(3))
        names.setdefault(key, len(names) + 1)
        return f"{m.group(1)}x2o{names[key]}"
    for u in us:
        u[0] = TEMP_RE.sub(ren, u[0])
    markers = len(re.findall(r"^[ \t]*%%[ \t]*x2o[ \t]+NON TRADUIT", text, re.M))
    approx = len(re.findall(r"^[ \t]*%%[ \t]*x2o[ \t]+approximation", text, re.M))
    return us, markers, approx


def covered(l0: int, l1: int, details: list[dict]) -> bool:
    for d in details:
        if d["ligne_oef"] and l0 <= d["ligne_oef"] <= l1:
            if d["niveau"] in ("approximation", "non_traduit") or (d["niveau"] == "info" and (d["regle"].startswith("G-") or d["construct"] in ("post-definition", "dropped-unread"))):   # D-16: dropped-unread is the report of an unread definition
                return True
    return False


def compare(o1_text: str, o2_text: str, details: list[dict]) -> dict:
    u1, m1, a1 = units(o1_text)
    u2, m2, a2 = units(o2_text)
    if u1 is None or u2 is None:
        return {"verdict": "DIFF-SILENT", "why": "O1 or O2 does not parse", "hunks": [], "markers_o1": m1}
    s1, s2 = [u[0] for u in u1], [u[0] for u in u2]
    sm = difflib.SequenceMatcher(None, s1, s2, autojunk=False)
    hunks, silent = [], 0
    for tag, i0, i1, j0, j1 in sm.get_opcodes():
        if tag == "equal":
            continue
        if i1 > i0:
            ok = all(covered(u1[k][1], u1[k][2], details) for k in range(i0, i1))
        else:   # unit only in O2: explained only if a neighbouring O1 unit carries a reported detail
            nb = [k for k in (i0 - 1, i0) if 0 <= k < len(u1)]
            ok = any(covered(u1[k][1], u1[k][2], details) for k in nb)
        hunks.append({"tag": tag, "o1": s1[i0:i1], "o2": s2[j0:j1], "explained": ok,
                      "o1_lines": [u1[i0][1], u1[i1 - 1][2]] if i1 > i0 else []})
        if not ok:
            silent += 1
    verdict = "IDENTICAL" if not hunks else ("DIFF-EXPLAINED" if not silent else "DIFF-SILENT")
    return {"verdict": verdict, "hunks": hunks, "markers_o1": m1, "approx_markers_o1": a1}


def run_forward(xml2oef: str, xml_dir: Path, out_dir: Path, xml_files: list[Path]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(xml_files), 200):
        subprocess.run([xml2oef, "-q", "-o", str(out_dir)] + [str(f) for f in xml_files[i:i + 200]],
                       capture_output=True, check=False)


def read(path: Path) -> str:
    return decode_bytes(path.read_bytes())[0]
