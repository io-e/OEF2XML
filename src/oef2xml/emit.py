"""Emitter (11.2 step 4): Program IR -> XML program bytes. Deterministic ids (REQ-OUT-3), one chain (REQ-OUT-4),
placeholders as orphan top-level blocks (REQ-TODO-1), 2-space indentation (REQ-OUT-1)."""
from __future__ import annotations

import hashlib
import sys

from lxml import etree

from .blocks import B
from .ids import make_id

NS = "urn:eleda:program:v1"
NSMAP = {None: NS}
PLACEHOLDER_X, PLACEHOLDER_Y0, PLACEHOLDER_DY = 700, -266, 220
INFO_X, INFO_Y = 61, -266
RAW_CAP = 4000


def _q(tag):
    return f"{{{NS}}}{tag}"


def placeholder_text(p, source_name: str, line_col) -> str:
    raw = p.raw
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    shown = raw if len(raw) <= RAW_CAP else raw[:RAW_CAP]
    l, c = line_col
    return f"TODO[OEF2XML {p.rule}] {p.reason} ({source_name}:{l}:{c}) | original: {shown} | sha256={sha}"


class Emitter:
    def __init__(self, prog, source_name: str, line_col_fn, carrier: str = "text", source_format: str = "ir", stamp: bool = False):
        self.p = prog
        self.src = source_name
        self.lc = line_col_fn
        self.carrier = carrier
        self.sf = source_format
        self.stamp = stamp
        self.vars: dict[str, str | None] = {}
        self.var_kind: dict[str, str | None] = {k: v for k, v in prog.variables}
        for k, v in prog.variables:
            self.vars.setdefault(k, v)

    def vid(self, name: str) -> str:
        return make_id(self.p.prog_id, "var:" + name)

    def use_var(self, name: str, kind=None):
        if name not in self.vars:
            self.vars[name] = kind
        elif kind and not self.vars[name]:
            self.vars[name] = kind

    def block(self, b: B, path: str, parent, tag="block", xy=None) -> etree._Element:
        el = etree.SubElement(parent, _q(tag), type=b.type, id=make_id(self.p.prog_id, path))
        if xy:
            el.set("x", str(xy[0]))
            el.set("y", str(xy[1]))
        if b.extra:
            es = etree.SubElement(el, _q("extraState"))
            for k, v in b.extra:
                etree.SubElement(es, _q(k)).text = v
        if b.comment:
            self.icons(el, b.comment)
        for name, text, var, vkind in b.fields:
            f = etree.SubElement(el, _q("field"), name=name)
            if var is not None:
                self.use_var(var, vkind)
                f.set("id", self.vid(var))
            else:
                f.text = text
        for name, sub, shadow in b.inputs:
            if sub is None:
                continue
            inp = etree.SubElement(el, _q("input"), name=name)
            if shadow:
                sh = etree.SubElement(inp, _q("shadow"), type=sub.type, id=make_id(self.p.prog_id, f"{path}/{name}"))
                for fname, text, var, _ in sub.fields:
                    etree.SubElement(sh, _q("field"), name=fname).text = text
            else:
                self.block(sub, f"{path}/{name}", inp)
        if b.next is not None:
            nx = etree.SubElement(el, _q("next"))
            self.block(b.next, path + "/next", nx)
        return el

    def icons(self, el, comment):
        text, pinned, h, w = comment
        ic = etree.SubElement(el, _q("icons"))
        etree.SubElement(ic, _q("comment"), text=text, pinned="True" if pinned else "False", height=str(h), width=str(w))

    def build(self) -> bytes:
        p = self.p
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 50000))   # <next> chains recurse once per block
        root = etree.Element(_q("eleda-program"), nsmap=NSMAP)
        root.set("id", p.prog_id)
        root.set("source_format", self.sf)
        etree.SubElement(root, _q("name")).text = p.name
        if p.author:
            etree.SubElement(root, _q("author")).text = p.author
        tags = etree.SubElement(root, _q("tags"))
        for t in p.tags:
            etree.SubElement(tags, _q("tag")).text = t
        langs = etree.SubElement(root, _q("langs"))
        for code, title, desc in p.langs:
            lg = etree.SubElement(langs, _q("lang"), code=code)
            etree.SubElement(lg, _q("title")).text = title
            etree.SubElement(lg, _q("description")).text = desc or None
        st = etree.SubElement(root, _q("settings"))
        etree.SubElement(st, _q("maxAttempts")).text = str(p.max_attempts)
        etree.SubElement(st, _q("hasNestedQuestion")).text = "false"
        if self.stamp:
            etree.SubElement(st, _q("createdAt")).text = "1970-01-01T00:00:00.000Z"
            etree.SubElement(st, _q("updatedAt")).text = "1970-01-01T00:00:00.000Z"
        vars_el = etree.SubElement(root, _q("variables"))
        blocks = etree.SubElement(root, _q("blocks"), languageVersion="0")
        info = B("info").f("default_title", p.title).f("default_lang", p.default_lang) \
            .f("default_description", p.description).f("max_attempts", str(p.max_attempts)).f("default_feedback", "false")
        if p.info_comment:
            info.comment = (p.info_comment, True, 107, 364)
        info.next = p.chain
        self.block(info, "info", blocks, xy=(INFO_X, INFO_Y))
        for k, ph in enumerate(p.placeholders):
            text = placeholder_text(ph, self.src, self.lc(ph.pos))
            if self.carrier == "display_element":
                pb = B("display_element", rule=ph.rule)
            else:
                pb = B("text", rule=ph.rule).f("TEXT", "")
            pb.comment = (text, True, 107, 364)
            self.block(pb, f"placeholder/{k}", blocks, xy=(PLACEHOLDER_X, PLACEHOLDER_Y0 + PLACEHOLDER_DY * k))
        for name, kind in self.vars.items():
            v = etree.SubElement(vars_el, _q("variable"), id=self.vid(name))
            if kind:
                v.set("type", kind)
            v.text = name
        etree.indent(root, space="  ")
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=False) + b"\n"
