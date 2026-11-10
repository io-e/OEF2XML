"""Semantic pass: statuses, gaps, taint, invariants (REQ-TODO-*, REQ-REP-4, REQ-SCH-*)."""
import json

from conftest import SIMPLE


def test_simple_is_complet_and_valid(conv):
    e, xml = conv(SIMPLE)
    assert e["statut"] == "complet" and e["rng"] == "ok" and e["xsd"] == "ok"
    assert e["blocs_question_emis"] == 1 and e["questions_gap"] == 0
    assert e["fidelite"] == "non_verifiee"          # never exacte while Q5 is open
    assert b'urn:eleda:program:v1' in xml and b"<eleda-program" in xml
    assert b"TODO[OEF2XML" not in xml


def test_deterministic(conv):
    a = conv(SIMPLE)
    b = conv(SIMPLE)
    assert a[1] == b[1]
    assert json.dumps(a[0], sort_keys=True) == json.dumps(b[0], sort_keys=True)


def test_no_question_is_partiel(conv):
    e, xml = conv("\\title{T}\n\\statement{Figure seule}\n")
    assert e["statut"] == "partiel" and "aucune_question" in e["flags"]
    assert e["fidelite"] is None and "sans_question" in e["flags"]          # D-22: not counted as approchee


def test_unknown_directive_becomes_gap_not_guess(conv):
    e, xml = conv(SIMPLE + "\\wims{x=1}\n")
    assert e["statut"] == "partiel"
    assert b"TODO[OEF2XML" in xml
    assert e["rng"] == "ok"


def test_trig_without_units_is_gap_and_taints(conv):
    src = ("\\title{T}\n\\real{a=random(1..2)}\n\\real{s=sin(\\a)}\n\\statement{x}\n"
           "\\answer{r}{\\s}{type=numeric}\n")
    e, xml = conv(src)
    assert e["statut"] == "partiel"
    assert e["questions_taint"] == 1 or e["questions_gap"] == 1
    assert any(k.startswith("G-") for k in e["gaps"])


def test_trig_units_deg_converts(conv):
    src = ("\\title{T}\n\\real{a=random(1..2)}\n\\real{s=sin(\\a)}\n\\statement{x}\n"
           "\\answer{r}{\\s}{type=numeric}\n")
    e, xml = conv(src, opts={"trig_units": "deg"})
    assert e["statut"] == "complet"


def test_invariants_i1_i2(conv):
    e, _ = conv(SIMPLE)
    assert e["questions_source"] == e["questions_converties"] + e["questions_gap"] + e["questions_taint"] \
        or e["questions_source"] >= e["blocs_question_emis"]
    assert e["directives_source"] == (e["directives_traduites"] + e["directives_approximees"]
                                      + e["directives_info"] + e["directives_non_traduites"])


def test_radio_choice(conv):
    src = ("\\title{T}\n\\statement{Choisir}\n\\choice{Q}{1}{oui,non}\n"
           "\\answer{Q}{\\choice}{type=radio}\n")
    # not asserting a particular status: no crash, valid XML or echec, never an invented placeholder-free guess
    e, xml = conv(src)
    assert e["statut"] in ("complet", "partiel", "echec")
    if xml:
        assert e["rng"] == "ok"


def test_no_crash_on_garbage(conv):
    for s in ["", "\\", "\\statement{", "\\answer{}", "\\if{", "\x00\x01"]:
        e, xml = conv(s)
        assert e["statut"] in ("complet", "partiel", "echec")


def test_strict_turns_partiel_into_echec(conv):
    e, xml = conv("\\title{T}\n\\statement{x}\n", strict=True)
    assert e["statut"] == "echec" and xml is None


# ---- v0.2.7 (owner review of PR #1) ----------------------------------------------------------------------------------

HEAD = "\\title{T}\n\\language{fr}\n"


def _details(e, construct):
    return [d for d in e["details"] if d["construct"] == construct]


def test_integer_rounding_always_reported_d20(conv):
    e, _ = conv(HEAD + "\\integer{a=randint(2..9)}\n\\integer{b=randint(2..9)}\n\\integer{c=\\a/\\b}\n\\statement{\\c}\n"
                "\\answer{R}{\\c}{type=numeric}\n")
    d = _details(e, "integer-rounding")
    assert len(d) == 1 and d[0]["niveau"] == "approximation" and d[0]["regle"] == "M-12"
    assert e["approximations"].get("integer-rounding") == 1


def test_integer_provably_integer_has_no_rounding_detail(conv):
    e, _ = conv(HEAD + "\\integer{a=randint(2..9)}\n\\integer{c=\\a+3}\n\\statement{\\c}\n\\answer{R}{\\c}{type=numeric}\n")
    assert _details(e, "integer-rounding") == []


def test_dropped_unread_cause_gap_d18(conv):
    # (a) the reader was replaced by a gap (G-23 \feedback reads \a); (b) nothing reads \z in the source
    e, _ = conv(HEAD + "\\integer{a=randint(2..9)}\n\\integer{z=3}\n\\statement{x}\n\\answer{R}{1}{type=numeric}\n\\feedback{1}{\\a}\n")
    du = {d["message"].split()[0]: d.get("cause_gap") for d in _details(e, "dropped-unread")}
    assert du.get("\\a") == "G-23"
    assert du.get("\\z") == "unread-in-source"


def test_dropped_unread_without_cause_has_no_cause_gap_d18(conv):
    # \a is read only by a definition placed after \statement: not a gap, not unread in the source -> no cause_gap
    e, _ = conv(HEAD + "\\integer{a=randint(2..9)}\n\\statement{x}\n\\answer{R}{1}{type=numeric}\n\\text{later=\\a}\n")
    d = [x for x in _details(e, "dropped-unread") if x["message"].startswith("\\a ")]
    assert d and all("cause_gap" not in x for x in d)


def test_roundtrip_comparator_accepts_only_caused_dropped_unread_d18():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import roundtrip as RT
    base = {"niveau": "info", "ligne_oef": 3, "colonne_oef": 1, "construct": "dropped-unread", "regle": "AC-8", "message": "m"}
    assert RT.covered(3, 3, [base]) is False
    assert RT.covered(3, 3, [dict(base, cause_gap="G-23")]) is True
    assert RT.covered(3, 3, [dict(base, cause_gap="unread-in-source")]) is True
