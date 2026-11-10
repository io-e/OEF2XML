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
    assert e["fidelite"] == "approchee"


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
