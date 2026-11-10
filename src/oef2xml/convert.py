"""Semantic pass (spec 11.2 step 3): OEF AST -> block IR, with taint, gaps, placeholders and counters.

Every decision cites a rule id (M-nn / G-nn / REQ-...). Constructs that cannot be converted become gaps
(placeholder + taint, file `partiel`): never guessed (REQ-TODO-2/3). Phase P1 scope (spec 15).
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

from . import expr as E
from . import textparse as T
from .blocks import B, arith, chain, count_types, get, num, setvar, txt
from .decode import DecodeError, decode_bytes, line_col
from . import shape
from .templates import TEMPLATES
from .parser import Block, Directive, ParseResult, parse

HEADER_NAMES = {"title", "language", "author", "description", "keywords", "email", "credits", "css", "observation",
                "computeanswer", "precision", "range", "format", "latex"}
TITLE_LANGS = {"title_en": "en", "title_fr": "fr", "title_es": "es", "title_it": "it",
               "title_ca": "ca", "title_cn": "cn", "title_nl": "nl", "title_si": "si"}
SCHEMA_LANGS = ("fr", "en", "es", "it", "de", "ar")
DEF_NAMES = {"integer", "int", "real", "rational", "text", "complex", "function", "matrix", "parameter", "variable", "mdef"}
VALUE_DEFS = {"integer", "int", "real", "rational", "text"}
GAP_DIRECTIVE_RULE = {  # directive -> (rule, construct, reason)
    "hint": ("G-03", "hint", "\\hint has no verified mapping (Q10)"),
    "help": ("G-03", "help", "\\help has no verified mapping (Q10)"),
    "solution": ("G-03", "solution", "\\solution is a worked solution, not the expected answer (Q10)"),
    "feedback": ("REQ-TODO-1", "feedback", "\\feedback is converted in phase 3 (8.5)"),
    "condition": ("G-15", "condition", "\\condition (answer analysis) is converted in phase 3"),
    "conditions": ("G-15", "conditions", "\\conditions (answer analysis) is converted in phase 3"),
    "steps": ("G-08", "steps", "\\steps: multi-step exercises are converted in phase 3 (9)"),
    "nextstep": ("G-08", "nextstep", "\\nextstep: dynamic step progression is a gap (REQ-STEP-2)"),
    "plot": ("G-09", "plot", "\\plot drawing has no conversion in this phase"),
    "wims": ("G-11", "wims-raw", "raw \\wims code has no mapping (spec silent, see docs/P1_QUESTIONS.md)"),
    "mdef": ("G-14", "mdef", "\\mdef module macro has no conversion"),
    "matrix": ("G-10", "matrix", "\\matrix is mapped in phase 2 (M-21, Q13)"),
    "function": ("M-22", "function", "\\function is mapped in phase 2 (M-22)"),
    "complex": ("G-11", "complex", "\\complex has no mapping (spec silent, see docs/P1_QUESTIONS.md)"),
    "parameter": ("G-11", "parameter", "\\parameter has no mapping (spec silent, see docs/P1_QUESTIONS.md)"),
    "variable": ("G-11", "variable", "\\variable has no mapping (spec silent, see docs/P1_QUESTIONS.md)"),
}
INTERACTIVE_TYPES = {"click", "mark", "clickfill", "dragfill", "multipleclick", "puzzle", "flashcard", "crossword",
                     "coord", "coordinates", "jsxgraphcurve", "chemdraw", "chemeq", "jmolclick", "vector", "matrix",
                     "set", "aset", "fset", "time", "units", "unit", "sigunits", "draw", "code", "compose",
                     "imgcomp", "javacurve", "link", "textcomp", "wordcomp", "wlist", "clicktile", "clock"}
NUMERIC_TYPES = {"numeric", "number"}
STRING_TYPES = {"default", "case", "text", "nocase", "atext", "chset", "raw"}
EXPR_TYPES = {"formal", "algexp", "expalg", "numexp", "function", "equation", "litexp", "symtext"}
PLANNED_TYPES = {"menu", "select", "correspond", "corresp", "reorder", "range", "ranges"}  # phase 2
TRUE_FALSE_PAIRS = {("Vrai", "Faux"), ("True", "False"), ("Vero", "Falso")}
RESERVED_VARS = re.compile(r"^(reply\d*|reply_\w*|result\d*|choice\d*|step\d*|sc_reply\d*|sc_choice\d*|imagedir|confparm[1-4])$")
X2O_TEMP = re.compile(r"\\?x2o(?:(?:rep)?\d+|version)(?![A-Za-z0-9])")
CTRL_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
SHA = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass
class Options:
    encoding: str = "auto"
    default_lang: str = "fr"
    max_attempts: int = 1
    source_format: str = "ir"
    id_from: str = "stem"
    trig_units: str | None = None
    html: str = "pass"
    strict: bool = False
    strict_limits: bool = False
    carrier: str = "text"
    idioms: bool = True
    stamp: bool = False


@dataclass
class Detail:
    niveau: str
    ligne_oef: int
    colonne_oef: int
    construct: str
    regle: str
    message: str

    def as_dict(self):
        return {"niveau": self.niveau, "ligne_oef": self.ligne_oef, "colonne_oef": self.colonne_oef,
                "construct": self.construct, "regle": self.regle, "message": self.message}


@dataclass
class Placeholder:
    rule: str
    reason: str
    pos: int
    raw: str
    construct: str


@dataclass
class Program:
    """result of the semantic pass, input of the emitter"""
    prog_id: str
    name: str
    author: str | None
    tags: list
    langs: list                  # [(code, title, description)]
    default_lang: str
    max_attempts: int
    title: str
    description: str
    variables: list              # [(name, kind)]  kind None|'QUESTION'
    chain: B | None
    placeholders: list
    info_comment: str


@dataclass
class Result:
    source: str
    status: str = "echec"
    program: Program | None = None
    details: list = field(default_factory=list)
    encoding: str = ""
    nbytes: int = 0
    title: str = ""
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    counters: dict = field(default_factory=dict)
    non_traduits: dict = field(default_factory=dict)
    approximations: dict = field(default_factory=dict)
    gaps: dict = field(default_factory=dict)
    flags: list = field(default_factory=list)
    copies: dict = field(default_factory=dict)
    dispositions: dict = field(default_factory=dict)
    n_directives: int = 0
    text: str = ""
    dyn: bool = False


def xml_clean(s: str) -> str:
    return CTRL_CHARS.sub(" ", s)



class Converter:
    def __init__(self, path: str, opts: Options):
        self.path = path
        self.opts = opts
        self.stem = path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0] if path else "program"
        self.details: list[Detail] = []
        self.placeholders: list[Placeholder] = []
        self.disp: dict[int, str] = {}             # directive pos -> traduite|approximee|info|non_traduite
        self.disp_construct: dict[int, str] = {}   # directive pos -> construct (non_traduite)
        self.tainted: dict[str, str] = {}          # variable -> origin rule
        self.declared: set[str] = set()
        self.list_vars: set[str] = set()
        self.int_vars: set[str] = set()
        self.var_order: list[str] = []
        self.loop_vars: set[str] = set()
        self.q_state: dict[int, str] = {}          # question directive pos -> converted|gap|taint
        self.q_copies: dict[int, int] = {}
        self.has_dyn = False
        self.extra_vars: list[tuple[str, str | None]] = []
        self.approx: Counter = Counter()
        self.header: dict = {}
        self.info_notes: list[str] = []
        self.numeric_notes: list[str] = []
        self.title_langs: list[tuple[str, str]] = []
        self.flags: list[str] = []
        self.shape_gaps = 0

    # ---------------------------------------------------------------- reporting helpers
    def lc(self, pos: int):
        return line_col(self.text, pos)

    def detail(self, level: str, pos: int, construct: str, rule: str, msg: str):
        l, c = self.lc(pos)
        self.details.append(Detail(level, l, c, construct, rule, msg))
        if level == "approximation":
            self.approx[construct] += 1

    def placeholder(self, rule: str, construct: str, reason: str, pos: int, raw: str):
        raw = xml_clean(raw)
        self.placeholders.append(Placeholder(rule, reason, pos, raw, construct))
        self.detail("non_traduit", pos, construct, rule, reason)

    def mark(self, d: Directive, how: str, construct: str = ""):
        if self.disp.get(d.pos) == "non_traduite":
            return
        self.disp[d.pos] = how
        if construct:
            self.disp_construct[d.pos] = construct

    def gap_directive(self, d: Directive, rule: str, construct: str, reason: str, raw: str | None = None):
        self.placeholder(rule, construct, reason, d.pos, raw if raw is not None else d.raw_text(self.text))
        self.disp[d.pos] = "non_traduite"
        self.disp_construct[d.pos] = construct

    # ---------------------------------------------------------------- driver
    def convert(self, raw: bytes) -> Result:
        res = Result(source=self.path, nbytes=len(raw))
        if len(raw) == 0:
            res.errors.append("Empty source file.")
            return res
        if len(raw) >= 199999:
            res.errors.append("Source file bad or too long.")
            return res
        try:
            text, enc = decode_bytes(raw, self.opts.encoding)
        except DecodeError as e:
            res.errors.append(str(e))
            return res
        res.encoding = enc
        cleaned = xml_clean(text)
        self.text = cleaned
        res.text = cleaned
        pr = parse(cleaned, self.opts.strict_limits)
        res.warnings = [(w[1], w[2]) for w in pr.warnings]
        if pr.errors:
            for pos, msg in pr.errors:
                l, c = self.lc(pos)
                res.errors.append(f"{msg} at line {l} col {c}.")
            return res
        if cleaned != text:
            self.detail("info", 0, "chars:illegal-xml", "REQ-IN-3", "characters not allowed in XML were replaced by spaces")
        for pos, code, msg in pr.warnings:
            if code == "LIMIT-1024":
                self.detail("info", pos, "limit:1024", "REQ-IN-5", "LIMIT-1024: " + msg)
        if enc != "utf-8":
            self.detail("info", 0, "encoding", "REQ-IN-3", f"source decoded as {enc}; output is UTF-8")
        self.pr = pr
        self.directives = pr.directives
        res.n_directives = len(pr.directives)
        self.run(pr, res)
        return res

    # ---------------------------------------------------------------- pre-pass (declarations, list typing, integer typing)
    def prepass(self):
        defs = []
        for d in self.directives:
            if d.name in VALUE_DEFS and d.name != "mdef" or d.name in ("complex", "matrix", "function", "parameter", "variable"):
                nm, _ = self.split_def(d)
                if nm:
                    self.declared.add(nm)
                    if nm not in self.var_order:
                        self.var_order.append(nm)
                    defs.append((nm, d))
            elif d.name == "for" and d.vals:
                m = re.match(r"\s*([A-Za-z_]\w*)\s*(=|in\b)", d.vals[0])
                if m:
                    self.declared.add(m.group(1))
                    self.loop_vars.add(m.group(1))
                    if m.group(1) not in self.var_order:
                        self.var_order.append(m.group(1))
        self.declared |= {"imagedir", "filedir", "confparm1", "confparm2", "confparm3", "confparm4"}
        listfn = re.compile(r"(?<![A-Za-z0-9_])(?:item|items|randitem|randomitem|shuffle)\s*\(")
        for d in self.directives:
            if d.name == "for" and d.vals:
                m = re.match(r"\s*[A-Za-z_]\w*\s*in\s+\\([A-Za-z_]\w*)\s*$", d.vals[0])
                if m:
                    self.list_vars.add(m.group(1))
            for v in d.vals:
                for m in listfn.finditer(v):
                    close = E.find_matching(v, m.end(), ")")
                    arg = v[m.end():close] if close > 0 else v[m.end():]
                    for mm in re.finditer(r"\\([A-Za-z_]\w*)", arg):
                        self.list_vars.add(mm.group(1))
                for mm in re.finditer(r"\\([A-Za-z_]\w*)\[([^\];]*)\]", v):
                    self.list_vars.add(mm.group(1))
        self.compute_int_vars(defs)

    def compute_int_vars(self, defs):
        parsed: dict[str, list] = {}
        for nm, d in defs:
            node = None
            if d.name in ("integer", "int"):
                node = "INT"
            elif d.name in ("real", "rational", "text"):
                _, rhs = self.split_def(d)
                try:
                    if rhs is None or "?" in rhs:
                        node = None
                    elif d.name == "text" and not re.fullmatch(r"\s*\\[A-Za-z_]\w*\s*", rhs):
                        node = None
                    else:
                        node = E.parse_expr(rhs.strip(), self.declared, self.opts.trig_units)
                except E.Unsupported:
                    node = None
            parsed.setdefault(nm, []).append(node)
        ints = {nm for nm, nodes in parsed.items() if all(n is not None for n in nodes)}
        changed = True
        while changed:
            changed = False
            for nm in sorted(ints):
                if any(n != "INT" and not self.prov_int(n, ints) for n in parsed[nm]):
                    ints.discard(nm)
                    changed = True
        self.int_vars = ints

    def prov_int(self, n, ints=None) -> bool:
        ints = self.int_vars if ints is None else ints
        if isinstance(n, E.Num):
            return re.fullmatch(r"-?\d+", n.text) is not None
        if isinstance(n, E.Var):
            return n.index is None and (n.name in ints)
        if isinstance(n, E.Un):
            return self.prov_int(n.a, ints)
        if isinstance(n, E.Bin):
            if n.op in ("+", "-", "*", "%"):
                return self.prov_int(n.a, ints) and self.prov_int(n.b, ints)
            if n.op == "^":
                return self.prov_int(n.a, ints) and isinstance(n.b, E.Num) and re.fullmatch(r"\d+", n.b.text) is not None
            return False
        if isinstance(n, E.Fn):
            if n.name in ("randint", "floor", "ceil", "rint", "items"):
                return True
            if n.name == "abs":
                return self.prov_int(n.args[0], ints)
        return False

    def snapshot(self):
        return (len(self.details), Counter(self.approx), len(self.extra_vars), self.q_counter, set(self.answer_vars))

    def restore(self, snap):
        del self.details[snap[0]:]
        self.approx = Counter(snap[1])
        del self.extra_vars[snap[2]:]
        self.q_counter = snap[3]
        self.answer_vars = set(snap[4])

    def lint(self, b: B) -> B:
        """REQ-SCH-2/4: a shape missing from the observed catalogue is never emitted: it becomes a gap"""
        pb = shape.problems(b)
        if pb:
            raise E.Unsupported("REQ-SCH-4", "shape", pb[0] + " (no real example of this shape)")
        return b

    # ---------------------------------------------------------------- definitions
    def split_def(self, d: Directive):
        """\\x{n=v} | \\x{n}{v} | \\x{n:=v} -> (name, rhs)"""
        if not d.vals:
            return "", None
        v0 = d.vals[0]
        v1 = d.vals[1] if len(d.vals) > 1 else ""
        if v1 == "" and "=" in v0:
            lhs, rhs = v0.split("=", 1)
            if lhs.endswith(":"):
                lhs = lhs[:-1]
        else:
            lhs, rhs = v0, v1
        lhs = lhs.strip()
        if lhs.startswith("\\"):
            lhs = lhs[1:]
        lhs = re.sub(r"\s+", "", lhs)
        if not re.fullmatch(r"[A-Za-z_]\w*", lhs):
            return "", None
        return lhs, rhs.replace("\r", "").replace("\n", " ").replace("\t", " ")

    def need_vars(self, names, pos=0):
        for nm in names:
            if RESERVED_VARS.match(nm) and not nm.startswith(("imagedir", "confparm")):
                raise E.Unsupported("G-18", "answer-ref", f"\\{nm} is a student-answer reference (feedback only)")
            if nm not in self.declared:
                raise E.Unsupported("M-42", "undeclared", f"undeclared variable \\{nm} (empty in WIMS)")
            if nm in self.tainted:
                raise E.Unsupported(self.tainted[nm], "taint", f"depends on {self.tainted[nm]} variable \\{nm} (REQ-TODO-3)")

    def check(self, node):
        self.need_vars(sorted(E.var_names(node)))

    # --- expression AST -> block tree
    def mk(self, node, ctx_int: bool, pos: int) -> B:
        """ctx_int: random(a..b) means randint (parmprep, sp.c:207)"""
        if isinstance(node, E.Num):
            return num(node.text, "M-12")
        if isinstance(node, E.Const):
            return B("math_constant", rule="M-12").f("CONSTANT", "PI")
        if isinstance(node, E.Str):
            return self.mk_text_node(node, pos, "M-13")
        if isinstance(node, E.Var):
            if node.index is not None:
                self.list_vars.add(node.name)
                idx = self.mk(node.index, False, pos)
                return B("list_short_get", rule="M-17").i("LIST", get(node.name)).i("INDEX", idx, idx.type == "math_number")
            return get(node.name)
        if isinstance(node, E.Un):
            a = self.mk(node.a, ctx_int, pos)
            return B("math_single", rule="M-12").f("OP", "NEG").i("NUM", a, a.type == "math_number")
        if isinstance(node, E.Bin):
            a = self.mk(node.a, ctx_int, pos)
            b = self.mk(node.b, ctx_int, pos)
            if node.op == "%":
                return (B("math_modulo", rule="M-12").i("DIVIDEND", a, a.type == "math_number")
                        .i("DIVISOR", b, b.type == "math_number"))
            op = {"+": "ADD", "-": "MINUS", "*": "MULTIPLY", "/": "DIVIDE", "^": "POWER"}[node.op]
            return arith(op, a, b, "M-12")
        if isinstance(node, E.Fn):
            return self.mk_fn(node, ctx_int, pos)
        raise E.Unsupported("G-11", "expr", f"unsupported node {type(node).__name__}")

    def mk_listarg(self, node, pos) -> B:
        if isinstance(node, E.Var):
            self.list_vars.add(node.name)
            return get(node.name)
        if isinstance(node, E.ListLit):
            return self.mk_list_literal(node.items, pos)
        return self.mk(node, False, pos)

    def mk_trig(self, node, pos) -> B:
        arg = node.args[0]
        units = self.opts.trig_units
        a = None
        if units == "deg":
            # forward idiom sin(x*pi/180): strip the factor (B.2); otherwise wrap x*180/pi (REQ-EXPR-4)
            if (isinstance(arg, E.Bin) and arg.op == "/" and isinstance(arg.b, E.Num) and arg.b.text == "180"
                    and isinstance(arg.a, E.Bin) and arg.a.op == "*" and isinstance(arg.a.b, E.Const)):
                a = self.mk(arg.a.a, False, pos)
            else:
                a = arith("DIVIDE", arith("MULTIPLY", self.mk(arg, False, pos), num("180", "REQ-EXPR-4"), "REQ-EXPR-4"),
                          B("math_constant", rule="REQ-EXPR-4").f("CONSTANT", "PI"), "REQ-EXPR-4")
        else:
            a = self.mk(arg, False, pos)
        self.detail("approximation", pos, f"trig:{node.name}", "REQ-EXPR-4",
                    f"{node.name}() mapped to math_trig with --trig-units {units}; fidelity non_verifiee (Q6)")
        return B("math_trig", rule="REQ-EXPR-4").f("OP", node.name.upper()).i("NUM", a, a.type == "math_number")

    def mk_fn(self, node, ctx_int, pos) -> B:
        n = node.name
        if n in ("sin", "cos", "tan"):
            return self.mk_trig(node, pos)
        if n == "randint" or (n == "random" and ctx_int):
            a, b = self.mk(node.args[0], False, pos), self.mk(node.args[1], False, pos)
            return (B("random_number", rule="M-10").f("type", "integer")
                    .i("min", a, a.type == "math_number").i("max", b, b.type == "math_number"))
        if n == "random":
            a, b = self.mk(node.args[0], False, pos), self.mk(node.args[1], False, pos)
            self.detail("approximation", pos, "random-real", "M-11",
                        "random(a..b) is a WIMS real in range; resolution may differ in the target platform")
            return (B("random_number", rule="M-11").f("type", "decimal")
                    .i("min", a, a.type == "math_number").i("max", b, b.type == "math_number"))
        if n in ("abs", "sqrt", "ln", "log10", "exp"):
            a = self.mk(node.args[0], ctx_int, pos)
            op = {"abs": "ABS", "sqrt": "ROOT", "ln": "LN", "log10": "LOG10", "exp": "EXP"}[n]
            return B("math_single", rule="M-12").f("OP", op).i("NUM", a, a.type == "math_number")
        if n in ("floor", "ceil", "rint"):
            a = self.mk(node.args[0], ctx_int, pos)
            op = {"floor": "ROUNDDOWN", "ceil": "ROUNDUP", "rint": "ROUND"}[n]
            return B("math_round", rule="M-12").f("OP", op).i("NUM", a, a.type == "math_number")
        if n == "shuffle":
            return B("shuffle_list", rule="M-15").i("LIST", self.mk_listarg(node.args[0], pos))
        if n == "randitem":
            return (B("lists_getIndex", rule="M-16").f("MODE", "GET").f("WHERE", "RANDOM")
                    .i("VALUE", self.mk_listarg(node.args[0], pos)))
        if n == "items":
            return B("lists_length", rule="M-18").i("VALUE", self.mk_listarg(node.args[0], pos))
        if n == "item":
            idx = self.mk(node.args[0], False, pos)
            return (B("list_short_get", rule="M-17").i("LIST", self.mk_listarg(node.args[1], pos))
                    .i("INDEX", idx, idx.type == "math_number"))
        raise E.Unsupported("G-11", f"fn:{n}", f"unsupported function {n}")

    def mk_list_literal(self, items: list[str], pos: int) -> B:
        lst = B("lists_create_with", rule="M-14").x("itemCount", str(len(items)))
        for k, it in enumerate(items):
            st = it.strip()
            if st != it:
                self.detail("approximation", pos, "list-item-whitespace", "M-14", "whitespace around list items trimmed")
            if re.fullmatch(r"-?\d+(\.\d+)?", st):
                item = num(st, "M-14")
            else:
                item = self.mk_text(st, pos, "M-14")
            lst.i(f"ADD{k}", item)
        return lst

    def mk_text_node(self, node: E.Str, pos: int, rule: str) -> B:
        blocks = []
        for p in node.parts:
            if isinstance(p, str):
                if p != "":
                    blocks.append(txt(p, rule))
            else:
                self.need_vars([p.name])
                if p.index is not None:
                    self.list_vars.add(p.name)
                    self.check(p.index)
                    idx = self.mk(p.index, False, pos)
                    blocks.append(B("list_short_get", rule="M-17").i("LIST", get(p.name)).i("INDEX", idx, idx.type == "math_number"))
                else:
                    blocks.append(get(p.name))
        if not blocks:
            return txt("", rule)
        if len(blocks) == 1:
            return blocks[0]
        j = B("text_join", rule=rule).x("itemCount", str(len(blocks)))
        for k, b in enumerate(blocks):
            j.i(f"ADD{k}", b)
        return j

    def mk_text(self, s: str, pos: int, rule: str = "M-13") -> B:
        node = E.parse_text_value(s, self.declared)
        if re.search(r"\\\(|\\\[", s):
            self.detail("approximation", pos, "text:latex-delimiters", rule,
                        "LaTeX delimiters kept as text; rendering in the target platform unverified (Q5)")
        if re.search(r"</?[A-Za-z]", s):
            self.detail("approximation", pos, "html:raw", "M-48",
                        "raw HTML kept verbatim in a text value (rendering unverified, Q5)")
        return self.mk_text_node(node, pos, rule)

    def has_ternary(self, s: str) -> bool:
        parts = E.split_top(s, "?")
        if len(parts) < 2:
            return False
        return bool(re.search(r"==|!=|<=|>=|<|>|(?<![=!<>])=(?!=)", parts[0]))

    _SPECIAL = None

    def special_in(self, s: str):
        if Converter._SPECIAL is None:
            from .parser import validator_module
            names = sorted(validator_module()._SPEC["special_functions"], key=len, reverse=True)
            Converter._SPECIAL = re.compile(r"(?<![\w\\])(" + "|".join(map(re.escape, names)) + r")\s*\(")
        return Converter._SPECIAL.findall(s)

    def build_def_value(self, d: Directive, name: str, rhs: str) -> B:
        kind = d.name
        ctx_int = kind in ("integer", "int")
        pos = d.pos
        if kind != "text" and self.has_ternary(rhs):     # a '?' inside a text value is plain text
            raise E.Unsupported("M-28", "ternary", "inline '?:' conditional in a definition (logic_ternary, phase 2)")
        if kind == "text":
            st = rhs.strip()
            if st == "":
                return txt("", "M-13")
            if self.special_in(st):
                node = E.parse_expr(st, self.declared, self.opts.trig_units)   # whole value must be one supported call
                self.check(node)
                return self.mk(node, False, pos)
            items = E.split_top(rhs, ",")
            if name in self.list_vars and len(items) > 1:
                for it in items:
                    self.need_vars(re.findall(r"\\([A-Za-z_]\w*)", it))
                return self.mk_list_literal(items, pos)
            return self.mk_text(rhs, pos, "M-13")
        node = E.parse_expr(rhs.strip(), self.declared, self.opts.trig_units)
        self.check(node)
        blk = self.mk(node, ctx_int, pos)
        if kind == "rational":
            self.detail("approximation", pos, "rational", "M-12", "\\rational value kept as an arithmetic expression (no rational type)")
        if ctx_int and not self.prov_int(node):
            # \integer{x=E} is rint(E) in WIMS (def.c putval): reproduced exactly with math_round ROUND
            blk = B("math_round", rule="M-12").f("OP", "ROUND").i("NUM", blk, blk.type == "math_number")
        return blk

    def conv_def(self, d: Directive):
        name, rhs = self.split_def(d)
        if not name or rhs is None:
            self.gap_directive(d, "G-11", f"def:{d.name}", "definition with an unusual name or without a value")
            return None
        if RESERVED_VARS.match(name) and not name.startswith(("imagedir", "confparm")):
            self.gap_directive(d, "G-18", f"def:{d.name}", f"\\{name} is a reserved WIMS name")
            self.tainted[name] = "G-18"
            return None
        snap = self.snapshot()
        try:
            val = self.lint(self.build_def_value(d, name, rhs))
        except E.Unsupported as e:
            self.restore(snap)
            self.gap_directive(d, e.rule, f"{d.name}:{e.construct}", e.reason)
            self.tainted[name] = e.rule
            return None
        if (X2O_TEMP.match(name) or X2O_TEMP.search(rhs or "")):
            self.detail("approximation", d.pos, "idiom:x2o-temporary", "REQ-IDIOM-2",
                        "forward-converter temporary kept as an ordinary variable (inlining of \\x2oN idioms is phase 2)")
        if name.endswith("_"):
            self.detail("approximation", d.pos, "def:name-trailing-underscore", "REQ-OUT-7",
                        "variable name ends with '_': kept verbatim; the target platform may strip the underscore")
        if d.name in ("integer", "int", "real", "rational") and re.fullmatch(r"\s*\\[A-Za-z_]\w*\s*", rhs or ""):
            self.detail("approximation", d.pos, "def:type-of-copy", "M-10",
                        "numeric type of a plain variable copy is not carried by the target platform (inferred from the source variable)")
        approx = any(x.niveau == "approximation" for x in self.details[snap[0]:])
        self.mark(d, "approximee" if approx else "traduite")
        return setvar(name, val, {"integer": "M-10", "int": "M-10", "real": "M-11", "rational": "M-12", "text": "M-13"}[d.name])


    # ---------------------------------------------------------------- control blocks (M-28, M-29, M-30)
    def mk_cond(self, node, pos) -> B:
        if isinstance(node, E.Logic):
            a, b = self.mk_cond(node.a, pos), self.mk_cond(node.b, pos)
            return B("logic_operation", rule="M-30").f("OP", node.op.upper()).i("A", a).i("B", b)
        if isinstance(node, E.Not):
            return B("logic_negate", rule="M-30").i("BOOL", self.mk_cond(node.a, pos))
        if isinstance(node, E.Cmp):
            a = self.mk_operand(node.a, pos)
            b = self.mk_operand(node.b, pos)
            lit_a = isinstance(node.a, E.Str) and all(isinstance(p, str) for p in node.a.parts)
            lit_b = isinstance(node.b, E.Str) and all(isinstance(p, str) for p in node.b.parts)
            num_a = isinstance(node.a, (E.Num, E.Bin, E.Un, E.Fn))
            num_b = isinstance(node.b, (E.Num, E.Bin, E.Un, E.Fn))
            if (lit_a and num_b) or (lit_b and num_a):
                self.detail("approximation", pos, "compare:text-number", "M-30", "text compared with a number")
            return B("logic_compare", rule="M-30").f("OP", node.op).i("A", a, a.type == "math_number").i("B", b, b.type == "math_number")
        raise E.Unsupported("G-11", "cond", "unsupported condition node")

    def mk_operand(self, node, pos) -> B:
        if isinstance(node, E.Str):
            if len(node.parts) == 1 and isinstance(node.parts[0], str) and re.fullmatch(r"-?\d+(\.\d+)?", node.parts[0].strip()):
                return num(node.parts[0].strip(), "M-30")
            return self.mk_text_node(node, pos, "M-13")
        return self.mk(node, False, pos)

    def declare_taint_in(self, items, rule):
        for it in items:
            if isinstance(it, Block):
                self.declare_taint_in(it.body, rule)
                self.declare_taint_in(it.orelse, rule)
            elif it.name in DEF_NAMES:
                nm, _ = self.split_def(it)
                if nm:
                    self.tainted.setdefault(nm, rule)

    def mark_all(self, items, how, construct):
        for it in items:
            if isinstance(it, Block):
                self.mark(it.head, how, construct)
                self.mark_all(it.body, how, construct)
                self.mark_all(it.orelse, how, construct)
            else:
                if it.name in ("answer", "reply", "choice"):
                    self.q_state.setdefault(it.pos, "gap")
                self.mark(it, how, construct)

    def gap_block(self, blk: Block, rule: str, construct: str, reason: str):
        end = blk.end if blk.end > 0 else blk.head.end
        raw = self.text[blk.head.pos:end]
        self.placeholder(rule, construct, reason, blk.head.pos, raw)
        self.declare_taint_in([blk], rule)
        self.disp[blk.head.pos] = "non_traduite"
        self.disp_construct[blk.head.pos] = construct
        self.mark_all(blk.body, "non_traduite", construct + ":in-gap")
        self.mark_all(blk.orelse, "non_traduite", construct + ":in-gap")

    def conv_block(self, blk: Block) -> list:
        h = blk.head
        kind = blk.kind
        try:
            if kind in ("if", "ifval", "while"):
                node = E.parse_condition(h.vals[0], self.declared, kind == "ifval", self.opts.trig_units)
                self.check_cond(node)
                cond = self.mk_cond(node, h.pos)
                body = self.conv_seq(blk.body)
                if kind == "while":
                    out = B("controls_whileUntil", rule="M-29").f("MODE", "WHILE").i("BOOL", cond).i("DO", chain(body))
                else:
                    els = self.conv_seq(blk.orelse) if blk.has_else else []
                    out = B("controls_if", rule="M-28")
                    if blk.has_else:
                        out.x("hasElse", "true")
                    out.i("IF0", cond).i("DO0", chain(body))
                    if blk.has_else:
                        out.i("ELSE", chain(els))
                self._x2o_cond_detail(h)
                self.mark(h, "traduite")
                return [out]
            if kind == "for":
                blk_out = self.conv_for(blk)
                self._x2o_cond_detail(h)
                return [blk_out]
        except E.Unsupported as e:
            self.gap_block(blk, e.rule, f"{kind}:{e.construct}", e.reason)
            return []
        self.gap_block(blk, "G-11", f"{kind}:unknown", "unknown control block")
        return []

    def _x2o_cond_detail(self, h):
        if X2O_TEMP.search(h.vals[0] if h.vals else ""):
            self.detail("approximation", h.pos, "idiom:x2o-temporary", "REQ-IDIOM-2",
                        "forward-converter temporary used in a control condition, kept as an ordinary variable (phase 2)")

    def check_cond(self, node):
        for n in E.walk(node):
            if isinstance(n, E.Var):
                self.need_vars([n.name])
            elif isinstance(n, E.Str):
                for p in n.parts:
                    if not isinstance(p, str):
                        self.need_vars([p.name])

    def conv_for(self, blk: Block) -> B:
        h = blk.head
        s = h.vals[0] if h.vals else ""
        m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s+to\s+(.+?)\s*$", s, re.I | re.S)
        m2 = re.match(r"^\s*([A-Za-z_]\w*)\s+in\s+(.+?)\s*$", s, re.I | re.S)
        if m:
            var = m.group(1)
            if re.search(r"\sstep\s", m.group(3), re.I):
                raise E.Unsupported("G-11", "for:step", "\\for with a step is not covered by the mapping")
            a = E.parse_expr(m.group(2), self.declared, self.opts.trig_units)
            b = E.parse_expr(m.group(3), self.declared, self.opts.trig_units)
            self.check(a)
            self.check(b)
            fa, fb = self.mk(a, True, h.pos), self.mk(b, True, h.pos)
            body = self.conv_seq(blk.body)
            self.mark(h, "traduite")
            return (B("controls_for", rule="M-29").f("VAR", "", var)
                    .i("FROM", fa, fa.type == "math_number").i("TO", fb, fb.type == "math_number")
                    .i("BY", num("1", "M-29"), True).i("DO", chain(body)))
        if m2:
            var = m2.group(1)
            lst = m2.group(2).strip()
            mv = re.fullmatch(r"\\([A-Za-z_]\w*)", lst)
            if not mv:
                raise E.Unsupported("G-11", "for:list", "\\for over a list that is not a plain variable")
            self.need_vars([mv.group(1)])
            self.list_vars.add(mv.group(1))
            body = self.conv_seq(blk.body)
            self.mark(h, "traduite")
            return B("controls_forEach", rule="M-29").f("VAR", "", var).i("LIST", get(mv.group(1))).i("DO", chain(body))
        raise E.Unsupported("G-11", "for:syntax", "\\for header not in the forms 'i=a to b' or 'x in \\L'")

    # ---------------------------------------------------------------- sequence
    def conv_seq(self, items) -> list:
        out = []
        for it in items:
            if isinstance(it, Block):
                if not it.head.post:
                    out.extend(self.conv_block(it))
                continue
            d = it
            nm = d.name
            if nm in HEADER_NAMES or nm in TITLE_LANGS or nm in ("statement", "answer", "reply", "choice"):
                continue                      # handled by the header / statement / question stages
            if d.pos in self.disp:
                continue
            if nm in ("integer", "int", "real", "rational", "text"):
                if d.post:
                    continue
                b = self.conv_def(d)
                if b is not None:
                    out.append(b)
            elif nm in GAP_DIRECTIVE_RULE:
                rule, cons, reason = GAP_DIRECTIVE_RULE[nm]
                self.gap_directive(d, rule, cons, reason)
                if nm in DEF_NAMES:
                    n, _ = self.split_def(d)
                    if n:
                        self.tainted.setdefault(n, rule)
            elif nm == "special":
                first = (d.vals[0].split() or [""])[0] if d.vals else ""
                if first in ("editarea", "help", "imagefill", "imageinput", "codeinput", "drawinput", "mathmlinput"):
                    self.gap_directive(d, "G-07", f"special:{first}", f"\\special {first} has no conversion")
                else:
                    self.gap_directive(d, "G-07", f"special:{first or 'empty'}", "\\special has no conversion")
            elif nm == "exit":
                self.gap_directive(d, "G-11", "exit", "\\exit has no conversion")
            else:
                self.gap_directive(d, "G-11", f"directive:{nm}", f"\\{nm} has no conversion (spec silent, see docs/P1_QUESTIONS.md)")
        return out

    def finish_post(self, items, in_post=False):
        """post-phase definitions (7.1): kept as info; their variables are tainted (never read by emitted constructs)"""
        for it in items:
            if isinstance(it, Block):
                if it.head.post:
                    self.mark_all([it], "info", "post-definition")
                    self.declare_taint_in([it], "REQ-OUT-4")
                    self.detail("info", it.head.pos, "post-definition", "REQ-OUT-4", "control block after \\statement (post-phase): used only by feedback (phase 3), not emitted")
                continue
            if it.post and it.name in ("integer", "int", "real", "rational", "text") and it.pos not in self.disp:
                self.mark(it, "info", "post-definition")
                n, _ = self.split_def(it)
                if n:
                    self.tainted.setdefault(n, "REQ-OUT-4")
                self.detail("info", it.pos, "post-definition", "REQ-OUT-4",
                            "definition after \\statement (post-phase): used only by feedback (phase 3), not emitted")


    # ---------------------------------------------------------------- statement (M-40..M-49)
    def latex_item(self, tok) -> B | None:
        body, display = tok.data
        parts = T.split_latex(body, self.declared)
        try:
            for p in parts:
                if not isinstance(p, str):
                    self.need_vars([p[1]])
        except E.Unsupported as e:
            self.placeholder(e.rule, "latex:" + e.construct, e.reason, tok.pos, tok.raw)
            return None
        if display:
            self.detail("approximation", tok.pos, "latex:display-math", "M-43",
                        "display math \\[...\\] has no distinct block; rendered like inline LaTeX")
        if all(isinstance(p, str) for p in parts):
            return B("latex", rule="M-43").i("LaTeX", txt(body, "M-43"))
        try:
            lp = B("latex_paragraph_create_with", rule="M-43").x("itemsCount", str(len(parts)))
            for k, p in enumerate(parts):
                if isinstance(p, str):
                    lp.i(f"ADD{k}", txt(p, "M-43"))
                else:
                    lp.i(f"ADD{k}", self.var_ref(p[1], p[2], tok.pos))
            return lp
        except E.Unsupported as e:
            self.placeholder(e.rule, "latex:" + e.construct, e.reason, tok.pos, tok.raw)
            return None

    def var_ref(self, name, idx, pos) -> B:
        self.need_vars([name])
        if idx is None:
            return get(name)
        node = E.parse_expr(idx.strip(), self.declared, self.opts.trig_units)
        self.check(node)
        self.list_vars.add(name)
        i = self.mk(node, False, pos)
        return B("list_short_get", rule="M-17").i("LIST", get(name)).i("INDEX", i, i.type == "math_number")

    def tok_items(self, toks) -> list:
        """tokens -> list of blocks for a richtext; gaps are recorded as placeholders and skipped"""
        out = []
        for t in toks:
            if t.kind == "text":
                if t.data != "":
                    out.append(txt(t.data, "M-41"))
            elif t.kind == "br":
                out.append(B("special_character", rule="M-45").f("character", "br"))
            elif t.kind == "hr":
                out.append(B("special_character", rule="M-45").f("character", "hr"))
            elif t.kind == "var":
                try:
                    out.append(self.var_ref(t.data[0], t.data[1], t.pos))
                except E.Unsupported as e:
                    self.placeholder(e.rule, "statement:" + e.construct, e.reason, t.pos, t.raw)
            elif t.kind == "latex":
                b = self.latex_item(t)
                if b is not None:
                    out.append(b)
            elif t.kind == "gap":
                self.placeholder(t.rule, t.construct, t.reason, t.pos, t.raw)
        return out

    def richtext(self, items: list) -> B | None:
        if not items:
            return None
        if all(i.type == "text" and i.fields[0][1].strip() == "" for i in items):
            return None
        rt = B("richtext_create_with", rule="M-41").x("itemsCount", str(len(items)))
        for k, it in enumerate(items):
            rt.i(f"ADD{k}", it)
        return rt

    def display(self, items: list, span=None) -> B | None:
        rt = self.richtext(items)
        if rt is None:
            return None
        blk = B("display_element", rule="M-40").i("object", rt)
        pb = shape.problems(blk)
        if pb:
            if span is not None:
                self.placeholder("REQ-SCH-4", "statement:shape", pb[0] + " (no real example of this shape)", span[0], span[1])
                self.shape_gaps += 1
            return None
        return blk

    def span_of(self, toks):
        if not toks:
            return None
        last = toks[-1]
        end = last.pos + len(last.raw if last.raw else (last.data if isinstance(last.data, str) else ""))
        return (toks[0].pos, self.text[toks[0].pos:end])

    def conv_statement(self, d: Directive, questions: list) -> list:
        s = d.vals[0] if d.vals else ""
        base = d.arg_starts[0] if d.arg_starts else d.pos
        toks = T.tokenize(s, base, self.declared, self.opts.html == "strict")
        n_gaps = sum(1 for t in toks if t.kind == "gap")
        for cls, cnt in T.html_classes(toks).items():
            if cls in ("b", "i", "strong", "em"):
                self.detail("approximation", d.pos, f"html:{cls}", "M-44", f"<{cls}> kept verbatim as text (markdown mapping not applied)")
            else:
                self.detail("approximation", d.pos, f"html:{cls}", "M-48",
                            f"<{cls}> kept verbatim in text ({cnt}x); rendering unverified (Q5)")
        out: list = []
        cur: list = []
        used: set = set()
        sg0 = self.shape_gaps
        qkey = {(q["kind"], q["n"]): q for q in questions}
        for t in toks:
            if t.kind != "embed":
                cur.append(t)
                continue
            kind, n, size = t.data
            q = qkey.get((kind, n))
            if q is None:
                self.placeholder("M-49", "embed:unknown", f"\\embed refers to {kind}{n}, which does not exist", t.pos, t.raw)
                n_gaps += 1
                continue
            if (kind, n) in used:
                self.placeholder("M-49", "embed:repeated", f"\\embed of {kind}{n} appears twice", t.pos, t.raw)
                n_gaps += 1
                continue
            used.add((kind, n))
            disp = self.display(self.tok_items(cur), self.span_of(cur))
            cur = []
            if disp is not None:
                out.append(disp)
            self.detail("approximation", t.pos, "embed", "M-49",
                        f"\\embed{{{kind}{n}}}: text before the marker is a display_element, the question follows (8.3)")
            if size:
                self.detail("approximation", t.pos, "embed:size", "M-49", "input size of \\embed ignored")
            q["embedded"] = True
            if q["block"] is not None:
                out.append(q["block"])
            else:
                self.detail("approximation", t.pos, "embed:dropped", "M-49",
                            f"\\embed{{{kind}{n}}} dropped: that question is a gap or tainted (see the placeholder of the question)")
        disp = self.display(self.tok_items(cur), self.span_of(cur))
        if disp is not None:
            out.append(disp)
        n_gaps += self.shape_gaps - sg0
        for q in questions:
            if not q.get("embedded") and q["block"] is not None:
                self.detail("info", q["d"].pos, "question:not-embedded", "M-49",
                            "question without \\embed: placed after the statement (as WIMS does)")
                out.append(q["block"])
        self.mark(d, "non_traduite" if n_gaps else "approximee", "statement:partial" if n_gaps else "")
        if not n_gaps:
            self.detail("approximation", d.pos, "statement", "M-40", "statement HTML/LaTeX assembled from blocks; rendering unverified (Q5)")
        return out


    # ---------------------------------------------------------------- questions (8)
    OPT_RE = re.compile(r"^\s*(type|option|options|weight)\s*=(.*)$", re.S | re.I)

    def qgap(self, q, rule, construct, reason, state="gap"):
        d = q["d"]
        self.gap_directive(d, rule, construct, reason)
        self.q_state[d.pos] = state
        q["block"] = None
        return None

    def new_qvars(self, q):
        base_a, base_q = "reponse", "question"
        a = base_a
        qn = base_q if self.q_counter == 0 else f"{base_q}{self.q_counter + 1}"
        while qn in self.declared:
            self.q_counter += 1
            qn = f"{base_q}{self.q_counter + 1}"
        self.q_counter += 1
        k = 0
        while a in self.declared and a not in self.answer_vars:      # never clash with an OEF variable (REQ-OUT-7)
            k += 1
            a = f"{base_a}_ans{k}" if k > 1 else f"{base_a}_ans"
        self.answer_vars.add(a)
        return a, qn

    def q_prompt(self, q, prompt: str) -> B | None:
        d = q["d"]
        pos = d.arg_starts[0] if d.arg_starts else d.pos
        toks = T.tokenize(prompt, pos, self.declared, self.opts.html == "strict")
        for t in toks:
            if t.kind == "embed":
                raise E.Unsupported("M-49", "prompt:embed", "\\embed inside a question prompt")
            if t.kind == "gap":
                raise E.Unsupported(t.rule, t.construct, t.reason)
        items = []
        for t in toks:
            if t.kind == "text":
                if t.data != "":
                    items.append(txt(t.data, "M-41"))
            elif t.kind == "br":
                items.append(B("special_character", rule="M-45").f("character", "br"))
            elif t.kind == "hr":
                items.append(B("special_character", rule="M-45").f("character", "hr"))
            elif t.kind == "var":
                items.append(self.var_ref(t.data[0], t.data[1], t.pos))
            elif t.kind == "latex":
                n0 = len(self.placeholders)
                b = self.latex_item(t)
                if b is None:
                    p = self.placeholders.pop()
                    self.details.pop()
                    raise E.Unsupported(p.rule, p.construct, p.reason)
                items.append(b)
        return self.richtext(items)

    def parse_q(self, d: Directive, kind: str):
        pos_vals, opts, typ, weight = [], [], None, None
        for v in d.vals:
            m = self.OPT_RE.match(v)
            if m and kind == "reply":
                key, val = m.group(1).lower(), m.group(2).strip()
                if key == "type":
                    typ = val
                elif key == "weight":
                    weight = val
                else:
                    opts.extend(val.replace(",", " ").split())
            elif m and kind == "choice" and m.group(1).lower() in ("option", "options", "weight"):
                key, val = m.group(1).lower(), m.group(2).strip()
                if key == "weight":
                    weight = val
                else:
                    opts.extend(val.replace(",", " ").split())
            else:
                pos_vals.append(v)
        return pos_vals, opts, typ, weight

    def conv_question(self, q):
        d = q["d"]
        kind = q["kind"]
        pos_vals, opts, typ, weight = self.parse_q(d, kind)
        snap = self.snapshot()
        try:
            return self._conv_question(q, d, kind, pos_vals, opts, typ, weight)
        except E.Unsupported as e:
            self.restore(snap)
            if e.construct == "taint":
                return self.qgap(q, e.rule, "answer:taint", e.reason, state="taint")
            return self.qgap(q, e.rule, f"answer:{e.construct}", e.reason)

    def q_options(self, q, d, opts, weight, choice_type: bool, checkbox: bool):
        for o in opts:
            ol = o.lower()
            if ol == "shuffle" and choice_type:
                self.detail("info", d.pos, "option:shuffle", "G-05", "option=shuffle on a choice type: target platform shuffling unknown")
            elif ol == "noorder" and checkbox:
                self.detail("info", d.pos, "option:noorder", "G-05", "option=noorder on a checkbox: no equivalent")
            else:
                self.detail("approximation", d.pos, f"option:{ol}", "G-05", f"option={o} has no equivalent (grading or display differs)")
        if weight is not None:
            self.detail("approximation", d.pos, "weight", "G-05", f"weight={weight} has no equivalent")

    def _conv_question(self, q, d, kind, pos_vals, opts, typ, weight):
        if kind == "reply":
            if len(pos_vals) > 2:
                raise E.Unsupported("G-05", "extra-param", "unrecognised extra parameter (not type/option/weight)")
            prompt = pos_vals[0] if pos_vals else ""
            expected = pos_vals[1] if len(pos_vals) > 1 else ""
            tname = "default" if typ is None else typ.strip()
            if tname.startswith("\\") or "\\" in tname:
                self.has_dyn = True
                raise E.Unsupported("G-06", "dynamic-type", f"answer type given as a variable ({tname}): decided at run time (REQ-IN-7)")
            tl = tname.lower()
            if tl in INTERACTIVE_TYPES:
                raise E.Unsupported("G-06", f"type:{tl}", f"answer type {tl} is interactive/module-defined")
            if tl in PLANNED_TYPES:
                raise E.Unsupported("G-06", f"type:{tl}", f"answer type {tl} is mapped in phase 2 (8.2)")
            known = NUMERIC_TYPES | STRING_TYPES | EXPR_TYPES | {"radio", "checkbox"}
            if tl not in known:
                raise E.Unsupported("G-06", f"type:{tl}", f"answer type {tl} not in the mapping table (8.1: passed through as raw replytype)")
            if re.match(r"\s*\\[A-Za-z_]\w*\s*$", expected) and re.match(r"\s*\\([A-Za-z_]\w*)", expected).group(1) not in self.declared \
                    and not RESERVED_VARS.match(re.match(r"\s*\\([A-Za-z_]\w*)", expected).group(1)):
                raise E.Unsupported("G-15", "analysed", "expected value is a name not yet defined: analysed answer (\\condition, 8.1)")
            if tl in ("radio", "checkbox"):
                return self.q_choice_from_answer(q, d, prompt, expected, tl, opts, weight)
            # open questions
            ptxt = self.q_prompt(q, prompt)
            a_var, q_var = self.new_qvars(q)
            if tl in NUMERIC_TYPES:
                node = E.parse_expr(expected.strip(), self.declared, self.opts.trig_units)
                self.check(node)
                if isinstance(node, E.Bin) and node.op == "/" and self.prov_int(node.a) and self.prov_int(node.b):
                    qtype = "fraction"
                    sol = (B("fraction", rule="M-12").i("dividend", self.mk(node.a, False, d.pos), True)
                           .i("divisor", self.mk(node.b, False, d.pos), True))
                    self.detail("approximation", d.pos, "answer:fraction", "REQ-MAP-Q-TEMPLATE", "expected a/b written as a fraction (target comparison unverified)")
                elif self.prov_int(node):
                    qtype, sol = "integer", self.mk(node, False, d.pos)
                else:
                    qtype, sol = "decimal", self.mk(node, False, d.pos)
                if self.header.get("precision") or self.header.get("range"):
                    self.detail("approximation", d.pos, "answer:precision", "M-07",
                                "\\precision/\\range of the exercise influence numeric comparison in WIMS and are not carried")
            elif tl in EXPR_TYPES:
                qtype, sol = "expression", self.mk_text(expected, d.pos, "M-22")
                self.detail("approximation", d.pos, f"answer:{tl}", "REQ-MAP-Q-TEMPLATE", "symbolic equivalence is graded by the target platform (unverified)")
            else:
                qtype, sol = "string", self.mk_text(expected, d.pos, "M-13")
                if tl not in ("default", "case", "text"):
                    self.detail("approximation", d.pos, f"answer:{tl}", "REQ-MAP-Q-TEMPLATE",
                                f"type {tl} (case-insensitive/any-of/raw) mapped to a plain string question")
            self.q_options(q, d, opts, weight, False, False)
            blk = self.lint(self.open_question("question_open", qtype, ptxt, sol, a_var, q_var, {}))
            return self.q_done(q, d, blk, a_var, q_var)
        # \choice
        prompt = pos_vals[0] if pos_vals else ""
        good = pos_vals[1] if len(pos_vals) > 1 else ""
        bad = pos_vals[2] if len(pos_vals) > 2 else ""
        if len(pos_vals) > 3:
            raise E.Unsupported("G-05", "extra-param", "unrecognised extra parameter of \\choice")
        gi, bi = self.split_items(good), self.split_items(bad)
        if not gi:
            raise E.Unsupported("G-06", "choice:no-good", "\\choice without right items")
        ptxt = self.q_prompt(q, prompt)
        sol = self.items_list(gi, d.pos)
        prop = self.items_list(bi, d.pos) if bi else None
        a_var, q_var = self.new_qvars(q)
        self.q_options(q, d, opts, weight, True, len(gi) > 1)
        self.detail("approximation", d.pos, "choice", "REQ-MAP-Q-TEMPLATE", "\\choice mapped to question_multiple_choices; unique when one right item (unverified)")
        blk = self.lint(self.open_question("question_multiple_choices", "unique" if len(gi) == 1 else "multiple", ptxt, sol,
                                           a_var, q_var, {"proposals": prop}))
        return self.q_done(q, d, blk, a_var, q_var)

    def split_items(self, s: str) -> list:
        s = s.strip()
        if s == "":
            return []
        return E.split_top(s, ",")

    def items_list(self, items, pos) -> B:
        node = [i for i in items]
        for it in node:
            self.need_vars(re.findall(r"\\([A-Za-z_]\w*)", it))
        lst = B("lists_create_with", rule="M-14").x("itemCount", str(len(node)))
        for k, it in enumerate(node):
            lst.i(f"ADD{k}", self.mk_text(it, pos, "M-13"))
        return lst

    def q_choice_from_answer(self, q, d, prompt, expected, tl, opts, weight):
        if ";" not in expected:
            raise E.Unsupported("G-06", f"{tl}:syntax", f"{tl} expected value without 'index;items' form")
        idx_s, items_s = expected.split(";", 1)
        items = self.split_items(items_s)
        if len(items) < 2:
            raise E.Unsupported("G-06", f"{tl}:items", f"{tl} with fewer than 2 items")
        idx_s = idx_s.strip()
        static = re.fullmatch(r"\d+(\s*,\s*\d+)*", idx_s) is not None
        ptxt = self.q_prompt(q, prompt)
        pair = False
        if len(items) == 2 and tl == "radio":
            pair = (items[0].strip(), items[1].strip()) in TRUE_FALSE_PAIRS
        if static:
            idxs = [int(x) for x in re.split(r"\s*,\s*", idx_s)]
            if len(set(idxs)) != len(idxs) or any(i < 1 or i > len(items) for i in idxs):
                raise E.Unsupported("G-06", f"{tl}:index", f"{tl} correct index out of range")
            if tl == "radio" and len(idxs) != 1:
                raise E.Unsupported("G-06", "radio:index", "radio with several correct indexes")
        else:
            if not pair:
                raise E.Unsupported("G-06", f"{tl}:dynamic-index", f"{tl} with a computed correct index (spec silent on complement, see P1_QUESTIONS)")
            node = E.parse_expr(idx_s, self.declared, self.opts.trig_units)
            self.check(node)
        a_var, q_var = self.new_qvars(q)
        self.q_options(q, d, opts, weight, True, tl == "checkbox")
        if pair:
            if static:
                sol = B("logic_boolean", rule="REQ-MAP-Q-TEMPLATE").f("BOOL", "TRUE" if idxs[0] == 1 else "FALSE")
            else:
                sol = (B("logic_compare", rule="REQ-MAP-Q-TEMPLATE").f("OP", "EQ").i("A", self.mk(node, False, d.pos)).i("B", num("1", "REQ-MAP-Q-TEMPLATE"), True))
            self.detail("approximation", d.pos, "answer:true-false", "REQ-MAP-Q-TEMPLATE", "radio on the language's true/false pair mapped to question_true_false")
            blk = self.lint(self.open_question("question_true_false", None, ptxt, sol, a_var, q_var, {}))
            return self.q_done(q, d, blk, a_var, q_var)
        good = [items[i - 1] for i in idxs]
        bad = [it for k, it in enumerate(items, 1) if k not in idxs]
        sol = self.items_list(good, d.pos)
        prop = self.items_list(bad, d.pos) if bad else None
        blk = self.lint(self.open_question("question_multiple_choices", "unique" if tl == "radio" else "multiple", ptxt, sol,
                                           a_var, q_var, {"proposals": prop}))
        return self.q_done(q, d, blk, a_var, q_var)

    def open_question(self, btype, qtype, ptxt, sol, a_var, q_var, extra) -> B:
        t = TEMPLATES[btype]
        b = B(btype, rule="REQ-MAP-Q-TEMPLATE")
        for k, v in t["extraState"]:
            b.x(k, v)
        for fname, fval in t["fields"]:
            if fval == "$type":
                if qtype is None:
                    continue
                b.f(fname, qtype)
            elif fval == "@answer":
                b.f(fname, "", a_var)
            elif fval == "@question":
                b.f(fname, "", q_var, "QUESTION")
            else:
                b.f(fname, fval)
        b.i("text", ptxt if ptxt is not None else B("text", rule="REQ-MAP-Q-TEMPLATE").f("TEXT", ""), ptxt is None)
        b.i("solution", sol, sol.type in ("math_number", "logic_boolean"))
        if extra.get("proposals") is not None:
            b.i("proposals", extra["proposals"])
        return b

    def q_done(self, q, d, blk, a_var, q_var):
        self.q_state[d.pos] = "converted"
        self.mark(d, "approximee")
        self.q_copies[d.pos] = 1
        self.detail("approximation", d.pos, "question", "REQ-REP-7",
                    "converted; grading semantics of the target platform unverified (Q5): fidelite non_verifiee")
        self.extra_vars.append((a_var, None))
        self.extra_vars.append((q_var, "QUESTION"))
        q["block"] = blk
        return blk


    # ---------------------------------------------------------------- header (M-01..M-08, G-01, G-02, G-04, G-16, G-20)
    def nested_positions(self, items, inside=False, acc=None):
        acc = set() if acc is None else acc
        for it in items:
            if isinstance(it, Block):
                self.nested_positions(it.body, True, acc)
                self.nested_positions(it.orelse, True, acc)
            elif inside:
                acc.add(it.pos)
        return acc

    def conv_header(self):
        seen = {}
        info_rule = {"email": "G-01", "credits": "G-02", "css": "G-02", "observation": "G-02", "format": "G-02",
                     "computeanswer": "G-02", "precision": "G-02", "range": "G-02", "latex": "G-16"}
        self.title = ""
        self.author = None
        self.desc = ""
        self.keywords = None
        self.lang_in = None
        self.lang_dyn = False
        for d in self.directives:
            nm = d.name
            if nm not in HEADER_NAMES and nm not in TITLE_LANGS:
                continue
            if d.pos in self.nested:
                self.gap_directive(d, "G-11", f"header:{nm}:conditional", f"\\{nm} inside a control block is evaluated at run time")
                continue
            val = d.vals[0] if d.vals else ""
            if nm in TITLE_LANGS:
                code = TITLE_LANGS[nm]
                if code in SCHEMA_LANGS and ("title_" + code) not in seen:
                    seen["title_" + code] = 1
                    self.title_langs.append((code, val.strip()))
                    self.mark(d, "traduite")
                elif code in SCHEMA_LANGS:
                    self.mark(d, "info")
                    self.detail("info", d.pos, "header:duplicate", "M-03", f"duplicate \\{nm}: first value kept")
                else:
                    self.gap_directive(d, "G-20", f"header:{nm}", f"language {code} has no lang element in the XML program: dropped")
                continue
            if nm in seen:
                self.mark(d, "info")
                self.detail("info", d.pos, "header:duplicate", "REQ-IN-2", f"duplicate \\{nm}: first value kept")
                continue
            seen[nm] = 1
            if nm == "title":
                if "\\" in val and re.search(r"\\[A-Za-z_]", val):
                    self.detail("info", d.pos, "title:variable", "M-01", "variable reference inside the title kept verbatim")
                self.title = xml_clean(" ".join(val.split()))
                if len(val.encode("utf-8")) > 80:
                    self.detail("approximation", d.pos, "title:length", "M-01", "title longer than 80 bytes (WIMS truncates; kept in full)")
                self.mark(d, "traduite")
            elif nm == "language":
                code = val.strip().lower()
                if code in SCHEMA_LANGS:
                    self.lang_in = code
                    self.mark(d, "traduite")
                else:
                    self.lang_dyn = True
                    self.lang_in = None
                    self.mark(d, "approximee")
                    self.detail("approximation", d.pos, "language", "G-04",
                                f"language {val.strip()!r} not available (ca cn nl si or dynamic): --default-lang {self.opts.default_lang} used")
            elif nm == "author":
                self.author = xml_clean(" ".join(val.split()))
                self.mark(d, "traduite")
            elif nm == "description":
                self.desc = xml_clean(val.strip())
                self.mark(d, "traduite")
            elif nm == "keywords":
                self.keywords = [k.strip() for k in re.split(r"[,;]", val) if k.strip()]
                self.mark(d, "approximee")
                self.detail("approximation", d.pos, "keywords", "M-06", "keywords mapped to tags (split on commas)")
            else:
                self.header[nm] = val
                self.mark(d, "info")
                rule = info_rule[nm]
                self.detail("info", d.pos, f"header:{nm}", rule, f"\\{nm} recorded in a comment of the info block, not converted")
                self.info_notes.append(f"\\{nm}: " + xml_clean(" ".join(val.split()))[:300])
        if self.lang_in is None and not self.lang_dyn:
            self.detail("info", 0, "language:default", "REQ-LANG-3", f"no \\language: --default-lang {self.opts.default_lang} used")
        self.detail("info", 0, "max_attempts", "M-08",
                    f"info.max_attempts={self.opts.max_attempts} comes from --max-attempts, default_feedback=false: not from the OEF")

    # ---------------------------------------------------------------- idioms (6.6)
    def scan_idioms(self):
        for m in re.finditer(r"^[ \t]*%%[ \t]*x2o[ \t]+NON TRADUIT[^\n]*", self.text, re.M):
            self.placeholder("G-22", "idiom:x2o-non-traduit", "block lost by the forward converter (REQ-IDIOM-1)", m.start(), m.group(0).strip())
        for m in re.finditer(r"^[ \t]*%%[ \t]*x2o[ \t]+approximation[^\n]*", self.text, re.M):
            self.detail("approximation", m.start(), "idiom:x2o-approximation", "REQ-IDIOM-1", m.group(0).strip()[:200])

    # ---------------------------------------------------------------- run
    def run(self, pr: ParseResult, res: Result):
        self.q_counter = 0
        self.answer_vars: set = set()
        self.nested = self.nested_positions(pr.items)
        self.prepass()
        self.scan_idioms()
        self.conv_header()
        pre = self.conv_seq(pr.items)
        self.finish_post(pr.items)
        # questions, in source order
        qs = []
        cnt = {"reply": 0, "choice": 0}
        for d in self.directives:
            if d.name in ("answer", "reply", "choice"):
                kind = "choice" if d.name == "choice" else "reply"
                cnt[kind] += 1
                qs.append({"d": d, "kind": kind, "n": cnt[kind], "block": None})
        for q in qs:
            d = q["d"]
            if d.pos in self.q_state:
                continue
            if d.pos in self.nested or d.post and False:
                self.qgap(q, "REQ-TODO-2", "answer:conditional",
                          "question defined inside a control block exists only conditionally (never guessed)")
                continue
            self.conv_question(q)
        stm = [d for d in self.directives if d.name == "statement"]
        body = list(pre)
        if stm:
            body.extend(self.conv_statement(stm[0], qs))
            for extra in stm[1:]:
                self.gap_directive(extra, "G-11", "statement:duplicate", "second \\statement")
        else:
            for q in qs:
                if q["block"] is not None:
                    body.append(q["block"])
        self.finalize(pr, res, qs, body)

    # ---------------------------------------------------------------- invariants, counters, program
    def finalize(self, pr, res, qs, body):
        miss = [d for d in self.directives if d.pos not in self.disp]
        if miss:
            res.errors.append("internal error: I1 violated, directive without disposition: " + ", ".join(
                f"\\{d.name}@{d.line}:{d.col}" for d in miss[:5]))
            return
        c = Counter(self.disp[d.pos] for d in self.directives)
        n_q = len(qs)
        qc = Counter(self.q_state.get(q["d"].pos, "?") for q in qs)
        if qc.get("?"):
            res.errors.append("internal error: I2 violated, question without disposition")
            return
        head = chain(body)
        types = count_types(head)
        q_blocks = sum(v for k, v in types.items() if k.startswith("question_"))
        copies = sum(self.q_copies.get(q["d"].pos, 0) for q in qs if self.q_state.get(q["d"].pos) == "converted")
        counters = {
            "questions_source": n_q, "questions_converties": qc.get("converted", 0), "questions_gap": qc.get("gap", 0),
            "questions_taint": qc.get("taint", 0), "blocs_question_emis": q_blocks,
            "directives_source": len(self.directives), "directives_traduites": c.get("traduite", 0),
            "directives_approximees": c.get("approximee", 0), "directives_info": c.get("info", 0),
            "directives_non_traduites": c.get("non_traduite", 0),
        }
        if n_q != counters["questions_converties"] + counters["questions_gap"] + counters["questions_taint"]:
            res.errors.append("internal error: I2 violated")
            return
        if len(self.directives) != counters["directives_traduites"] + counters["directives_approximees"] + \
                counters["directives_info"] + counters["directives_non_traduites"]:
            res.errors.append("internal error: I1 violated")
            return
        if q_blocks != copies:
            res.errors.append("internal error: I3 violated (question blocks emitted != sum of copies)")
            return
        res.counters = counters
        res.copies = {f"{q['d'].line}:{q['d'].col}": self.q_copies.get(q["d"].pos, 0) for q in qs}
        res.dispositions = dict(c)
        res.non_traduits = dict(sorted(Counter(p.construct for p in self.placeholders).items()))
        res.gaps = dict(sorted(Counter(p.rule for p in self.placeholders).items()))
        res.approximations = dict(sorted(self.approx.items()))
        res.details = self.details
        res.dyn = self.has_dyn
        flags = []
        if q_blocks == 0:
            flags.append("aucune_question")
        if self.has_dyn:
            flags.append("type_dynamique")
        res.flags = flags
        res.status = "partiel" if (self.placeholders or q_blocks == 0) else "complet"
        res.title = self.title
        res.program = self.make_program(head, res)

    def make_program(self, head, res) -> Program:
        stem = self.stem
        if self.opts.id_from == "hash":
            pid = "h" + hashlib.sha1(self.text.encode("utf-8")).hexdigest()[:16]
        else:
            pid = stem
        lang = self.lang_in or self.opts.default_lang
        title = self.title or stem
        langs = [(lang, title, self.desc)]
        for code, t in self.title_langs:
            if code != lang:
                langs.append((code, t or title, ""))
        tags = []
        for k in (self.keywords or []):
            if k not in tags:
                tags.append(k)
        tags.append("TODO")
        # variables actually referenced + question variables (REQ-OUT-7)
        notes = list(self.info_notes)
        if self.placeholders:
            ids = Counter(p.rule for p in self.placeholders)
            notes.append("TODO[OEF2XML] " + str(len(self.placeholders)) + " placeholder(s): " +
                         ", ".join(f"{k} x{v}" for k, v in sorted(ids.items())))
        return Program(prog_id=pid, name=title, author=self.author, tags=tags, langs=langs, default_lang=lang,
                       max_attempts=self.opts.max_attempts, title=title, description=self.desc,
                       variables=list(self.extra_vars), chain=head, placeholders=self.placeholders,
                       info_comment="\n".join(notes))


def convert_bytes(path: str, raw: bytes, opts: Options) -> Result:
    """public entry: bytes of one OEF -> Result (never raises for OEF content; internal errors become echec)"""
    cv = Converter(path, opts)
    try:
        return cv.convert(raw)
    except Exception as ex:  # REQ-BATCH-1: a crash is an echec entry, never a lost entry
        r = Result(source=path, nbytes=len(raw))
        r.errors.append(f"internal error: {type(ex).__name__}: {ex}")
        r.flags.append("crash")
        return r
