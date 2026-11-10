"""Table-driven-ish OEF expression parser (REQ-EXPR-1/2/6).

Parses the numeric/boolean expression subset of OEF definitions and conditions into a small AST.
Anything outside the supported grammar raises `Unsupported(rule, reason)`: the caller turns it into a
gap (REQ-EXPR-6: never a best-effort partial tree).
The function-name -> rule table below plays the role of expr_spec.json (REQ-EXPR-1); it is derived from
spec 7.2/7.3 and Appendix A.3.3.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


class Unsupported(Exception):
    def __init__(self, rule: str, construct: str, reason: str):
        super().__init__(reason)
        self.rule, self.construct, self.reason = rule, construct, reason


# --- AST --------------------------------------------------------------------------------
@dataclass
class Num:
    text: str


@dataclass
class Var:
    name: str
    index: object = None      # Expr for \L[i]


@dataclass
class Const:
    name: str                  # 'pi'


@dataclass
class Un:
    op: str                    # 'neg'
    a: object


@dataclass
class Bin:
    op: str                    # + - * / ^ %
    a: object
    b: object


@dataclass
class Fn:
    name: str
    args: list = field(default_factory=list)


@dataclass
class ListLit:
    items: list                # list of raw item strings


@dataclass
class Cmp:
    op: str                    # EQ NEQ LT LTE GT GTE
    a: object
    b: object


@dataclass
class Logic:
    op: str                    # AND OR
    a: object
    b: object


@dataclass
class Not:
    a: object


@dataclass
class Str:
    parts: list                # [str | Var]


# --- function tables (REQ-EXPR-3, A.3.3) ---------------------------------------------------
SUPPORTED_FN = {"abs", "sqrt", "ln", "log10", "exp", "floor", "ceil", "rint",
                "randint", "random", "pickone", "item", "items", "randitem", "randomitem", "shuffle"}
TRIG_FN = {"sin", "cos", "tan", "asin", "acos", "atan", "arcsin", "arccos", "arctan"}
# unsupported function -> (rule, construct family). P = planned later phase (behaves as gap).
GAP_FN = {
    "pari": "G-11", "maxima": "G-11", "yacas": "G-11", "solve": "G-11", "int": "G-11", "integral": "G-11",
    "integrate": "G-11", "det": "G-11", "determinant": "G-11", "mathexp_cut": "G-11",
    "wims": "G-12", "slib": "G-13",
    "draw": "G-09", "drawtikz": "G-09", "canvasdraw": "G-09", "teximg": "G-09",
    "evalue": "M-23", "evaluate": "M-23", "diff": "M-24", "deriv": "M-24", "derivative": "M-24",
    "simplify": "M-25",
    "row": "M-21", "rows": "M-21", "column": "M-21", "randrow": "M-21", "randomrow": "M-21",
    "position": "M-19", "positionof": "M-19",
    "asis": "M-40", "texmath": "M-40", "htmlmath": "M-40",
}
NUM_RE = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def find_matching(s: str, i: int, close: str) -> int:
    """liblines.c find_matching: s[i] is the char after the opener; returns index of closer or -1."""
    par = brk = brc = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "[": brk += 1
        elif ch == "]": brk -= 1
        elif ch == "(": par += 1
        elif ch == ")": par -= 1
        elif ch == "{": brc += 1
        elif ch == "}": brc -= 1
        else:
            i += 1
            continue
        if par < 0 or brk < 0 or brc < 0:
            if ch != close or par > 0 or brk > 0 or brc > 0:
                return -1
            return i
        i += 1
    return -1


def split_top(s: str, sep: str) -> list[str]:
    """split on a one-character separator outside (), [], {}"""
    out, cur, depth = [], [], 0
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def split_top_dots(s: str) -> list[str] | None:
    """split `a..b` at the first top-level '..' (sp_random: first top-level ',' or '..')."""
    depth = 0
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and s.startswith("..", i):
            return [s[:i], s[i + 2:]]
        i += 1
    return None


class ExprParser:
    """Precedence climbing over a string. `declared`: names of OEF variables (a reference to any
    other name is an Unsupported 'undeclared variable', M-42)."""

    def __init__(self, src: str, declared: set[str], trig_units: str | None = None):
        self.s = src
        self.i = 0
        self.declared = declared
        self.trig_units = trig_units

    # -- helpers
    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\n\r":
            self.i += 1

    def peek(self) -> str:
        self.ws()
        return self.s[self.i] if self.i < len(self.s) else ""

    def eat(self, ch: str) -> bool:
        if self.peek() == ch:
            self.i += 1
            return True
        return False

    def fail(self, reason: str, rule: str = "G-11"):
        raise Unsupported(rule, "expr", reason)

    # -- grammar
    def parse(self):
        node = self.expr()
        self.ws()
        if self.i != len(self.s):
            self.fail(f"cannot parse expression near {self.s[self.i:self.i+20]!r}")
        return node

    def expr(self):
        a = self.term()
        while True:
            c = self.peek()
            if c in ("+", "-"):
                self.i += 1
                b = self.term()
                a = Bin(c, a, b)
            else:
                return a

    def term(self):
        a = self.unary()
        while True:
            c = self.peek()
            if c in ("*", "/", "%"):
                self.i += 1
                b = self.unary()
                a = Bin(c, a, b)
            else:
                return a

    def unary(self):
        c = self.peek()
        if c == "-":
            self.i += 1
            a = self.unary()
            if isinstance(a, Num) and not a.text.startswith("-"):
                return Num("-" + a.text)
            return Un("neg", a)
        if c == "+":
            self.i += 1
            return self.unary()
        return self.power()

    def power(self):
        a = self.atom()
        if self.peek() == "^":
            self.i += 1
            b = self.unary()
            return Bin("^", a, b)
        return a

    def atom(self):
        c = self.peek()
        if c == "":
            self.fail("unexpected end of expression")
        if c == "(":
            self.i += 1
            node = self.expr()
            if not self.eat(")"):
                self.fail("missing )")
            return node
        m = NUM_RE.match(self.s, self.i)
        if m and (c.isdigit() or c == "."):
            self.i = m.end()
            return Num(m.group(0))
        if c == "\\":
            return self.varref()
        m = NAME_RE.match(self.s, self.i)
        if m:
            name = m.group(0)
            j = m.end()
            k = j
            while k < len(self.s) and self.s[k] in " \t\n":
                k += 1
            if k < len(self.s) and self.s[k] == "(":
                close = find_matching(self.s, k + 1, ")")
                if close < 0:
                    self.fail("unmatched parenthesis in call")
                argstr = self.s[k + 1:close]
                self.i = close + 1
                return self.call(name, argstr)
            if name == "pi":
                self.i = j
                return Const("pi")
            self.fail(f"bare word {name!r} in numeric expression")
        self.fail(f"unexpected character {c!r}")

    def varref(self):
        m = NAME_RE.match(self.s, self.i + 1)
        if not m:
            self.fail("bad variable reference", "M-42")
        name = m.group(0)
        self.i = m.end()
        idx = None
        if self.i < len(self.s) and self.s[self.i] == "[":
            close = find_matching(self.s, self.i + 1, "]")
            if close < 0:
                self.fail("unmatched [", "M-42")
            inner = self.s[self.i + 1:close]
            self.i = close + 1
            if ";" in inner:
                raise Unsupported("M-21", "matrix-cell", f"matrix cell reference \\{name}[{inner}] (phase 2, Q13)")
            idx = ExprParser(inner, self.declared, self.trig_units).parse()
        return Var(name, idx)

    def call(self, name: str, argstr: str):
        if name in SUPPORTED_FN:
            return self.supported_call(name, argstr)
        if name in TRIG_FN:
            if self.trig_units in ("deg", "rad") and name in ("sin", "cos", "tan"):
                if len(split_top(argstr, ",")) != 1:
                    self.fail(f"{name}() expects one argument")
                return Fn(name, [self.sub(argstr)])
            why = ("units unconfirmed, Q6: use --trig-units" if name in ("sin", "cos", "tan")
                   else "inverse trigonometric function: result unit not covered by REQ-EXPR-4")
            raise Unsupported("G-21", f"trig:{name}", f"trigonometric function {name}() ({why})")
        rule = GAP_FN.get(name)
        if rule:
            raise Unsupported(rule, f"fn:{name}", f"function {name}() has no mapping in this phase")
        raise Unsupported("G-11", f"fn:{name}", f"unknown function {name}()")

    def supported_call(self, name: str, argstr: str):
        if name in ("randint", "random", "pickone"):
            parts = split_top(argstr, ",")
            if len(parts) > 1:                              # comma form: item pick (sp_random)
                return Fn("randitem", [ListLit([p for p in parts])])
            dd = split_top_dots(argstr)
            if dd is None:
                self.fail(f"{name}() without a range")
            fn = "randint" if name in ("randint", "pickone") else "random"
            return Fn(fn, [self.sub(dd[0]), self.sub(dd[1])])
        if name in ("abs", "sqrt", "ln", "log10", "exp", "floor", "ceil", "rint"):
            if len(split_top(argstr, ",")) != 1:
                self.fail(f"{name}() expects one argument")
            return Fn(name, [self.sub(argstr)])
        if name in ("shuffle", "randitem", "randomitem", "items"):
            return Fn("randitem" if name == "randomitem" else name, [self.listarg(argstr)])
        if name == "item":
            parts = split_top(argstr, ",")
            if len(parts) < 2:
                self.fail("item() expects an index and a list")
            idx = parts[0].strip()
            if idx.startswith("(") and idx.endswith(")"):
                idx = idx[1:-1]
            if ".." in idx:
                raise Unsupported("G-12", "fn:item-range", "item(a..b, L) range form")
            rest = ",".join(parts[1:])
            return Fn("item", [self.sub(idx), self.listarg(rest)])
        self.fail(f"unsupported call {name}")

    def sub(self, s: str):
        return ExprParser(s, self.declared, self.trig_units).parse()

    def listarg(self, s: str):
        st = s.strip()
        m = re.fullmatch(r"\\([A-Za-z_]\w*)", st)
        if m:
            return Var(m.group(1))
        return ListLit(split_top(st, ","))


def parse_expr(src: str, declared: set[str], trig_units: str | None = None):
    return ExprParser(src, declared, trig_units).parse()


# --- conditions (M-28, M-30) -------------------------------------------------------------
CMP_OPS = [("==", "EQ"), ("!=", "NEQ"), ("<>", "NEQ"), ("<=", "LTE"), (">=", "GTE"), ("<", "LT"), (">", "GT"), ("=", "EQ")]
WORD_RE = re.compile(r"(?<![\w\\])(and|or|not)(?![\w])")


def _tokenize_cond(s: str):
    """tokens: ('(', ')', 'cmp', op), ('log', 'and'|'or'|'not'), ('chunk', text) at any depth"""
    toks = []
    cur = []
    i = 0
    n = len(s)

    def flush():
        if cur:
            if "".join(cur).strip() != "":      # whitespace between tokens is not significant
                toks.append(("chunk", "".join(cur)))
            cur.clear()

    while i < n:
        ch = s[i]
        if ch == "\\":                      # \name or \name[...] stays inside the chunk
            m = NAME_RE.match(s, i + 1)
            if m:
                j = m.end()
                if j < n and s[j] == "[":
                    c = find_matching(s, j + 1, "]")
                    if c > 0:
                        j = c + 1
                cur.append(s[i:j]); i = j
                continue
            cur.append(ch); i += 1
            continue
        if ch in "()":
            flush(); toks.append((ch, ch)); i += 1; continue
        matched = False
        for sym, op in CMP_OPS:
            if s.startswith(sym, i):
                # '<' / '>' ... but not part of '<=' handled by order; '=' alone ok
                flush(); toks.append(("cmp", op)); i += len(sym); matched = True
                break
        if matched:
            continue
        m = WORD_RE.match(s, i) if (i == 0 or not (s[i - 1].isalnum() or s[i - 1] in "_\\")) else None
        if m:
            flush(); toks.append(("log", m.group(1))); i = m.end(); continue
        cur.append(ch); i += 1
    flush()
    return toks


class CondParser:
    def __init__(self, s: str, declared: set[str], numeric: bool, trig_units: str | None = None):
        self.trig_units = trig_units
        self.toks = _tokenize_cond(s)
        self.p = 0
        self.declared = declared
        self.numeric = numeric           # \ifval: operands must be numeric expressions

    def peek(self):
        return self.toks[self.p] if self.p < len(self.toks) else (None, None)

    def parse(self):
        node = self.p_or()
        if self.p != len(self.toks):
            raise Unsupported("M-30", "cond", "cannot parse condition")
        return node

    def p_or(self):
        a = self.p_and()
        while self.peek() == ("log", "or"):
            self.p += 1
            a = Logic("OR", a, self.p_and())
        return a

    def p_and(self):
        a = self.p_not()
        while self.peek() == ("log", "and"):
            self.p += 1
            a = Logic("AND", a, self.p_not())
        return a

    def p_not(self):
        if self.peek() == ("log", "not"):
            self.p += 1
            return Not(self.p_not())
        return self.p_cmp()

    def group_has_logic(self, start: int):
        """toks[start] == '(' : does the matching group contain a cmp/log token at its own level?"""
        depth = 0
        k = start
        while k < len(self.toks):
            t = self.toks[k][0]
            if t == "(":
                depth += 1
            elif t == ")":
                depth -= 1
                if depth == 0:
                    return False, k
            elif depth == 1 and t in ("cmp", "log"):
                return True, k
            k += 1
        return False, -1

    def p_cmp(self):
        t = self.peek()
        if t[0] == "(":
            has, _ = self.group_has_logic(self.p)
            if has:
                self.p += 1
                node = self.p_or()
                if self.peek()[0] != ")":
                    raise Unsupported("M-30", "cond", "missing ) in condition")
                self.p += 1
                return node
        a = self.operand()
        if self.peek()[0] == "cmp":
            op = self.peek()[1]
            self.p += 1
            b = self.operand()
            return self.make_cmp(op, a, b)
        raise Unsupported("M-30", "cond", "condition without comparison operator")

    def operand(self):
        """collect tokens up to a depth-0 cmp/log token or an unmatched ')'"""
        depth = 0
        parts = []
        while self.p < len(self.toks):
            t, v = self.toks[self.p]
            if t == "(":
                depth += 1
            elif t == ")":
                if depth == 0:
                    break
                depth -= 1
            elif t in ("cmp", "log") and depth == 0:
                break
            parts.append(v if t == "chunk" else ("(" if t == "(" else ")" if t == ")" else (v if t == "log" else _OPSYM[v])))
            self.p += 1
        if not parts:
            raise Unsupported("M-30", "cond", "empty operand")
        return "".join(parts)

    def make_cmp(self, op, a, b):
        return Cmp(op, self.to_val(a), self.to_val(b))

    def to_val(self, s: str):
        try:
            return ExprParser(s, self.declared, self.trig_units).parse()
        except Unsupported as e:
            if self.numeric or e.rule not in ("G-11",):
                raise
        # \if (text comparison): literal text with \var interpolation
        return parse_text_value(s.strip())


_OPSYM = {"EQ": "==", "NEQ": "!=", "LT": "<", "LTE": "<=", "GT": ">", "GTE": ">="}


def parse_text_value(s: str, declared: set | None = None):
    """text with \\name references -> Str(parts). Inside \\( .. \\) / \\[ .. \\] only *declared* names are references
    (LaTeX commands such as \\nearrow stay literal), as in the statement tokenizer."""
    parts: list = []
    cur: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\\":
            if declared is not None and i + 1 < n and s[i + 1] in "([":
                close = "\\)" if s[i + 1] == "(" else "\\]"
                j = s.find(close, i + 2)
                if j >= 0:
                    cur.append(s[i:i + 2])
                    k = i + 2
                    while k < j:
                        if s[k] == "\\":
                            m = NAME_RE.match(s, k + 1)
                            if m and m.group(0) in declared and m.end() <= j:
                                if cur:
                                    parts.append("".join(cur)); cur = []
                                e = m.end()
                                idx = None
                                if e < j and s[e] == "[":
                                    c = find_matching(s, e + 1, "]")
                                    if 0 < c < j and ";" not in s[e + 1:c]:
                                        idx = ExprParser(s[e + 1:c], declared).parse()
                                        e = c + 1
                                parts.append(Var(m.group(0), idx))
                                k = e
                                continue
                            if m:
                                cur.append(s[k:m.end()]); k = m.end(); continue
                            cur.append(s[k:k + 2]); k += 2; continue
                        cur.append(s[k]); k += 1
                    cur.append(close)
                    i = j + 2
                    continue
            m = NAME_RE.match(s, i + 1)
            if m:
                if cur:
                    parts.append("".join(cur)); cur = []
                j = m.end()
                idx = None
                if j < n and s[j] == "[":
                    c = find_matching(s, j + 1, "]")
                    if c < 0:
                        raise Unsupported("M-42", "textvalue", "unmatched [")
                    inner = s[j + 1:c]
                    if ";" in inner:
                        raise Unsupported("M-21", "matrix-cell", "matrix cell reference")
                    idx = ExprParser(inner, set()).parse()
                    j = c + 1
                parts.append(Var(m.group(0), idx))
                i = j
                continue
        cur.append(ch)
        i += 1
    if cur:
        parts.append("".join(cur))
    return Str(parts)


def parse_condition(src: str, declared: set[str], numeric: bool, trig_units: str | None = None):
    return CondParser(src.strip(), declared, numeric, trig_units).parse()


def walk(node):
    """yield every sub-node (depth first)"""
    yield node
    if isinstance(node, (Bin, Cmp, Logic)):
        yield from walk(node.a); yield from walk(node.b)
    elif isinstance(node, (Un, Not)):
        yield from walk(node.a)
    elif isinstance(node, Fn):
        for a in node.args:
            yield from walk(a)
    elif isinstance(node, Var) and node.index is not None:
        yield from walk(node.index)
    elif isinstance(node, Str):
        for p in node.parts:
            if not isinstance(p, str):
                yield from walk(p)


def var_names(node) -> set[str]:
    return {n.name for n in walk(node) if isinstance(n, Var)}
