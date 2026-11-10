"""Shape lint on the block tree (REQ-SCH-2/3/4): used while converting so that a block shape missing from the
observed catalogue (e.g. a list longer than any observed one) becomes a gap instead of being emitted."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).with_name("data")


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads((DATA / "xml_block_catalog.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _never() -> frozenset:
    return frozenset(catalog()["enum_types_never_observed"])


def problems(b, acc: list | None = None) -> list[str]:
    """names of fields, inputs, extraState children and the block type itself that the catalogue does not know"""
    acc = [] if acc is None else acc
    cat = catalog()["blocks"]
    while b is not None:
        info = cat.get(b.type)
        if info is None or b.type in _never():
            acc.append(f"block type {b.type!r} not in the catalogue")
        else:
            for n, _, _, _ in b.fields:
                if n not in info["fields"]:
                    acc.append(f"{b.type}: field {n!r} not in the catalogue")
            for n, sub, shadow in b.inputs:
                if sub is None:
                    continue
                if n not in info["inputs"]:
                    acc.append(f"{b.type}: input {n!r} not in the catalogue")
                if shadow and sub.type not in catalog()["shadow_types"]:
                    acc.append(f"shadow type {sub.type!r} never observed as a shadow")
            for n, _ in b.extra:
                if n not in info["extraState"]:
                    acc.append(f"{b.type}: extraState {n!r} not in the catalogue")
        for _, sub, _ in b.inputs:
            if sub is not None:
                problems(sub, acc)
        b = b.next
    return acc
