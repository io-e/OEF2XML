"""Block tree used between the semantic pass and the emitter (11.2 steps 3-4)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class B:
    type: str
    fields: list = field(default_factory=list)   # (name, text, varname|None, kind) ; varname -> <field name id=..> empty
    inputs: list = field(default_factory=list)   # (name, B, shadow: bool)
    extra: list = field(default_factory=list)    # (name, text)
    comment: tuple | None = None                 # (text, pinned, height, width)
    next: "B | None" = None
    xy: tuple | None = None
    rule: str = ""                               # M-nn / G-nn / REQ- id that produced the block (traceability)

    def f(self, name, text="", var=None, vkind=None):
        self.fields.append((name, text, var, vkind))
        return self

    def i(self, name, blk, shadow=False):
        self.inputs.append((name, blk, shadow))
        return self

    def x(self, name, text):
        self.extra.append((name, text))
        return self


def num(text: str, rule: str = "") -> B:
    return B("math_number", rule=rule).f("NUM", text)


def txt(text: str, rule: str = "") -> B:
    return B("text", rule=rule).f("TEXT", text)


def get(name: str) -> B:
    return B("variables_get").f("VAR", "", name)


def setvar(name: str, value: B, rule: str = "") -> B:
    return B("variables_set", rule=rule).f("VAR", "", name).i("VALUE", value)


def arith(op: str, a: B, b: B, rule: str = "") -> B:
    return B("math_arithmetic", rule=rule).f("OP", op).i("A", a, a.type == "math_number").i("B", b, b.type == "math_number")


def chain(blocks: list) -> "B | None":
    """link a list of blocks through <next>; returns head"""
    head = None
    prev = None
    for b in blocks:
        if b is None:
            continue
        if head is None:
            head = b
        else:
            prev.next = b
        prev = b
        while prev.next is not None:
            prev = prev.next
    return head


def count_types(b: "B | None", acc: dict | None = None) -> dict:
    acc = {} if acc is None else acc
    while b is not None:
        acc[b.type] = acc.get(b.type, 0) + 1
        for _, sub, _ in b.inputs:
            count_types(sub, acc)
        b = b.next
    return acc


def to_dict(b: "B | None") -> dict | None:
    """JSON-serialisable form for --dump-ir (REQ-ARCH-1)"""
    if b is None:
        return None
    return {"type": b.type, "rule": b.rule,
            "fields": [[n, t, v] for n, t, v, _ in b.fields],
            "inputs": {n: to_dict(s) for n, s, _ in b.inputs},
            "extra": b.extra, "comment": list(b.comment) if b.comment else None,
            "next": to_dict(b.next)}
