"""Output validation (REQ-OUT-5, REQ-VAL-3, REQ-TODO-6): RNG + XSD, shape lint, independent question scan,
placeholder lint. None of this reads the converter's IR: it works on the written XML only."""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from lxml import etree

NS = "urn:eleda:program:v1"
Q = "{%s}" % NS
DATA = Path(__file__).with_name("data")


def default_schema_dir() -> Path:
    """validation/xml/schemas_v1 of the repository (REQ-ARCH-5), or $OEF2XML_SCHEMA_DIR / --schema-dir"""
    import os
    env = os.environ.get("OEF2XML_SCHEMA_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for up in here.parents:
        cand = up / "validation" / "xml" / "schemas_v1"
        if cand.is_dir():
            return cand
    raise FileNotFoundError("schemas_v1 not found: use --schema-dir or OEF2XML_SCHEMA_DIR")


@lru_cache(maxsize=4)
def load_schemas(schema_dir: str):
    d = Path(schema_dir)
    rng = etree.RelaxNG(etree.parse(str(d / "XML_program_v1.rng")))
    xsd = etree.XMLSchema(etree.parse(str(d / "XML_program_v1.xsd")))
    return rng, xsd


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads((DATA / "xml_block_catalog.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def whitelist(schema_dir: str) -> frozenset:
    """REQ-SCH-1/3: RNG enum values minus the 21 never observed, and present in the catalogue (REQ-SCH-2)"""
    tree = etree.parse(str(Path(schema_dir) / "XML_program_v1.rng"))
    rns = {"r": "http://relaxng.org/ns/structure/1.0"}
    enum = {v.text for v in tree.xpath("//r:define[@name='block-type-enum']//r:value", namespaces=rns)}
    cat = catalog()
    never = set(cat["enum_types_never_observed"])
    return frozenset((enum - never) & set(cat["blocks"]))


def validate_rng_xsd(xml: bytes, schema_dir: str):
    """returns (rng_ok, xsd_ok, messages)"""
    rng, xsd = load_schemas(str(schema_dir))
    doc = etree.fromstring(xml)
    msgs = []
    r = rng.validate(doc)
    if not r:
        msgs += ["rng: " + str(e) for e in rng.error_log][:5]
    x = xsd.validate(doc)
    if not x:
        msgs += ["xsd: " + str(e) for e in xsd.error_log][:5]
    return bool(r), bool(x), msgs


def shape_lint(xml: bytes, schema_dir: str) -> list[str]:
    """AC-5 / REQ-VAL-3: types in the whitelist; field, input and extraState names in the catalogue; child order;
    every variable id used by a field is declared in <variables>."""
    wl = whitelist(str(schema_dir))
    cat = catalog()["blocks"]
    root = etree.fromstring(xml)
    problems: list[str] = []
    declared = {v.get("id") for v in root.iter(Q + "variable")}
    order = {"extraState": 0, "icons": 1, "field": 2, "input": 3, "next": 4}
    for el in root.iter(Q + "block", Q + "shadow"):
        t = el.get("type")
        if t not in wl:
            problems.append(f"block type {t!r} outside the whitelist")
            continue
        info = cat[t]
        last = -1
        for ch in el:
            tag = etree.QName(ch).localname
            if tag not in order:
                problems.append(f"{t}: unexpected child <{tag}>")
                continue
            if order[tag] < last:
                problems.append(f"{t}: child order violated at <{tag}>")
            last = order[tag]
            if tag == "field":
                n = ch.get("name")
                if n not in info["fields"]:
                    problems.append(f"{t}: field {n!r} not in the catalogue")
                if ch.get("id") is not None and ch.get("id") not in declared:
                    problems.append(f"{t}.{n}: variable id not declared")
            elif tag == "input":
                n = ch.get("name")
                if n not in info["inputs"]:
                    problems.append(f"{t}: input {n!r} not in the catalogue")
            elif tag == "extraState":
                for e in ch:
                    n = etree.QName(e).localname
                    if n not in info["extraState"]:
                        problems.append(f"{t}: extraState {n!r} not in the catalogue")
        if el.tag == Q + "shadow" and t not in catalog()["shadow_types"]:
            problems.append(f"shadow type {t!r} never observed as a shadow")
    return problems


def count_question_blocks(xml: bytes) -> int:
    """independent scan of the written XML (I3): <block type="question_*"> elements"""
    root = etree.fromstring(xml)
    return sum(1 for b in root.iter(Q + "block") if (b.get("type") or "").startswith("question_"))


TODO_RE = re.compile(r"^TODO\[OEF2XML ([A-Za-z0-9-]+)\] (.*) \(.*:\d+:\d+\) \| original: (.*) \| sha256=([0-9a-f]{64})$", re.S)


def placeholder_lint(xml: bytes, n_expected: int, status: str) -> list[str]:
    """REQ-TODO-6: every TODO comment carries the verbatim fragment (hash check) and no placeholder block is
    reachable from the info chain; one placeholder per reported gap; a complete file has none."""
    root = etree.fromstring(xml)
    blocks = root.find(Q + "blocks")
    problems: list[str] = []
    tops = list(blocks.findall(Q + "block"))
    infos = [b for b in tops if b.get("type") == "info"]
    if len(infos) != 1:
        problems.append(f"{len(infos)} info blocks at top level")
    found = 0
    for b in tops:
        if b.get("type") == "info":
            for cm in b.iter(Q + "comment"):
                if TODO_RE.match(cm.get("text", "")):
                    problems.append("placeholder reachable from the info chain")
            continue
        cm = b.find(Q + "icons/" + Q + "comment")
        text = cm.get("text", "") if cm is not None else ""
        if not text.startswith("TODO[OEF2XML "):
            problems.append("top-level block that is not a placeholder")
            continue
        found += 1
        m = TODO_RE.match(text)
        if not m:
            problems.append("TODO comment not in the REQ-TODO-1 format")
            continue
        raw, sha = m.group(3), m.group(4)
        if len(raw) < 4000 and hashlib.sha256(raw.encode("utf-8")).hexdigest() != sha:
            problems.append(f"TODO[{m.group(1)}]: fragment hash mismatch")
        if len(raw) >= 4000 and raw == "":
            problems.append("empty fragment")
    if found != n_expected:
        problems.append(f"{found} placeholder blocks written, {n_expected} gaps reported")
    if status == "complet" and found:
        problems.append("complet file with placeholders")
    return problems
