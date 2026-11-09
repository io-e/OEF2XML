"""Statement / text-fragment tokenizer (M-40..M-49, spec 7.5, A.3.5).

Turns the raw text of \\statement into tokens. Unconvertible tokens become `gap` tokens carrying their
rule id; nothing is interpreted beyond the shapes listed in the spec (never invent, REQ-TODO-2).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .expr import NAME_RE, find_matching

TEXT_CMD_GROUPS = {"if": 3, "ifval": 3, "for": 2, "exit": 0, "img": 1, "audio": 1, "slib": 1,
                   "special": 1, "draw": 2, "drawtikz": 2, "canvasdraw": 2, "embed": 1}
CMD_RULE = {"if": ("M-40", "statement:text-control"), "ifval": ("M-40", "statement:text-control"),
            "for": ("M-40", "statement:text-control"), "exit": ("M-40", "statement:text-control"),
            "img": ("M-47", "statement:img"), "audio": ("M-47", "statement:audio"),
            "slib": ("G-13", "statement:slib"), "special": ("G-07", "statement:special"),
            "draw": ("G-09", "statement:draw"), "drawtikz": ("G-09", "statement:draw"),
            "canvasdraw": ("G-09", "statement:draw")}
ANSWER_TIME = re.compile(r"^(reply\d*|reply_\w*|result\d*|choice\d*|step\d*|sc_reply\d*|sc_choice\d*)$")
ASSET_NAMES = {"imagedir", "filedir"} | {f"confparm{i}" for i in range(1, 5)}
TAG_RE = re.compile(r"</?([A-Za-z][A-Za-z0-9]*)\b[^>]*>")
BR_RE = re.compile(r"<br\s*/?>", re.I)
HR_RE = re.compile(r"<hr\s*/?>", re.I)
EMBED_RE = re.compile(r"^\s*(reply|choice|r|c)\s*(\d+)\s*(?:,(.*))?$", re.S | re.I)


@dataclass
class Tok:
    kind: str            # text var latex embed br hr gap
    pos: int             # absolute offset in the source
    data: object = None
    raw: str = ""
    rule: str = ""
    construct: str = ""
    reason: str = ""


def _groups(s: str, i: int, maxg: int):
    """consume up to maxg {..} groups after position i; returns (end, [group texts])"""
    out = []
    j = i
    n = len(s)
    while len(out) < maxg:
        k = j
        while k < n and s[k] in " \t\n\r":
            k += 1
        if k < n and s[k] == "{":
            c = find_matching(s, k + 1, "}")
            if c < 0:
                break
            out.append(s[k + 1:c])
            j = c + 1
        else:
            break
    return j, out


def tokenize(s: str, base: int, declared: set[str], html_strict: bool = False) -> list[Tok]:
    toks: list[Tok] = []
    buf: list[str] = []
    bstart = [0]
    n = len(s)
    i = 0

    def flush(upto):
        if buf:
            toks.append(Tok("text", base + bstart[0], "".join(buf)))
            buf.clear()

    def add_gap(start, end, rule, construct, reason):
        flush(start)
        toks.append(Tok("gap", base + start, None, s[start:end], rule, construct, reason))

    def put(ch_start, text):
        if not buf:
            bstart[0] = ch_start
        buf.append(text)

    while i < n:
        ch = s[i]
        if ch == "\\":
            nxt = s[i + 1] if i + 1 < n else ""
            if nxt == "\\":
                put(i, "\\\\"); i += 2; continue
            if nxt in "([":
                close = "\\)" if nxt == "(" else "\\]"
                j = s.find(close, i + 2)
                if j < 0:
                    put(i, ch); i += 1; continue
                flush(i)
                toks.append(Tok("latex", base + i, (s[i + 2:j], nxt == "["), s[i:j + 2]))
                i = j + 2
                continue
            m = NAME_RE.match(s, i + 1)
            if m:
                name = m.group(0)
                j = m.end()
                if name in TEXT_CMD_GROUPS:
                    k = j
                    while k < n and s[k] in " \t\n\r":
                        k += 1
                    if (k < n and s[k] == "{") or name == "exit":
                        end, groups = _groups(s, j, TEXT_CMD_GROUPS[name])
                        if name == "embed":
                            em = EMBED_RE.match(groups[0]) if groups else None
                            flush(i)
                            if em:
                                kind = "reply" if em.group(1).lower() in ("reply", "r") else "choice"
                                toks.append(Tok("embed", base + i, (kind, int(em.group(2)), em.group(3)), s[i:end]))
                            else:
                                toks.append(Tok("gap", base + i, None, s[i:end], "M-49", "embed:dynamic",
                                                "\\embed with a non-literal argument"))
                            i = end
                            continue
                        rule, construct = CMD_RULE[name]
                        add_gap(i, end, rule, construct, f"text-level \\{name}{{...}} has no conversion in this phase")
                        i = end
                        continue
                if ANSWER_TIME.match(name):
                    add_gap(i, j, "G-18", "statement:answer-ref", f"\\{name} refers to a student answer (feedback only)")
                    i = j; continue
                if name in ASSET_NAMES:
                    add_gap(i, j, "M-47", "statement:asset", f"\\{name} asset reference (images are phase 2)")
                    i = j; continue
                if name in declared:
                    idx = None
                    jj = j
                    if jj < n and s[jj] == "[":
                        c = find_matching(s, jj + 1, "]")
                        if c > 0:
                            idx = s[jj + 1:c]
                            jj = c + 1
                    flush(i)
                    toks.append(Tok("var", base + i, (name, idx), s[i:jj]))
                    i = jj
                    continue
                add_gap(i, j, "M-42", "statement:undeclared", f"\\{name} is not a declared variable (becomes empty in WIMS)")
                i = j
                continue
            put(i, ch); i += 1; continue
        if ch == "<":
            m = BR_RE.match(s, i)
            if m:
                flush(i); toks.append(Tok("br", base + i, None, m.group(0))); i = m.end(); continue
            m = HR_RE.match(s, i)
            if m:
                flush(i); toks.append(Tok("hr", base + i, None, m.group(0))); i = m.end(); continue
            m = TAG_RE.match(s, i)
            if m:
                tag = m.group(1).lower()
                if tag == "img":
                    add_gap(i, m.end(), "M-47", "statement:img", "<img> becomes an image block in phase 2"); i = m.end(); continue
                if tag in ("script", "form"):
                    close = re.search(r"</%s\s*>" % tag, s[i:], re.I)
                    end = i + close.end() if close else m.end()
                    add_gap(i, end, "G-19", f"statement:{tag}", f"<{tag}> element cannot be carried"); i = end; continue
                if tag == "input":
                    add_gap(i, m.end(), "G-19", "statement:input", "<input> element cannot be carried"); i = m.end(); continue
                if html_strict:
                    add_gap(i, m.end(), "G-17", f"statement:html:{tag}", "HTML carried as a placeholder (--html strict)")
                    i = m.end(); continue
                put(i, m.group(0)); i = m.end(); continue
        put(i, ch); i += 1
    flush(n)
    return toks


def html_classes(toks: list[Tok]) -> dict[str, int]:
    """element classes of raw HTML kept verbatim in text tokens (M-48): tag -> count"""
    out: dict[str, int] = {}
    for t in toks:
        if t.kind == "text":
            for m in TAG_RE.finditer(t.data):
                out[m.group(1).lower()] = out.get(m.group(1).lower(), 0) + 1
    return dict(sorted(out.items()))


def split_latex(body: str, declared: set[str]):
    """latex body -> list of str | ('var', name, idx). Only declared variable names are substituted."""
    parts: list = []
    cur: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        if ch == "\\":
            m = NAME_RE.match(body, i + 1)
            if m and m.group(0) in declared:
                if cur:
                    parts.append("".join(cur)); cur = []
                j = m.end()
                idx = None
                if j < n and body[j] == "[":
                    c = find_matching(body, j + 1, "]")
                    if c > 0:
                        idx = body[j + 1:c]; j = c + 1
                parts.append(("var", m.group(0), idx))
                i = j
                continue
            if m:
                cur.append(body[i:m.end()]); i = m.end(); continue
            if i + 1 < n:
                cur.append(body[i:i + 2]); i += 2; continue
        cur.append(ch); i += 1
    if cur:
        parts.append("".join(cur))
    return parts
