"""AC-5 shape lint and AC-11 placeholder lint on written XML."""
from oef2xml import validate as V
from oef2xml.validate import default_schema_dir


def test_shape_lint_clean_on_converted(conv):
    e, xml = conv("\\title{T}\n\\integer{a=randint(1..5)}\n\\statement{A \\a}\n\\answer{p}{\\a}{type=numeric}\n")
    assert V.shape_lint(xml, str(default_schema_dir())) == []


def test_shape_lint_detects_unknown_type(conv):
    e, xml = conv("\\title{T}\n\\statement{x}\n\\answer{p}{1}{type=numeric}\n")
    bad = xml.replace(b'type="question_open"', b'type="not_a_block"')
    assert bad != xml
    assert V.shape_lint(bad, str(default_schema_dir()))


def test_placeholder_lint_counts(conv):
    e, xml = conv("\\title{T}\n\\statement{x}\n\\wims{y=1}\n\\answer{p}{1}{type=numeric}\n")
    from lxml import etree
    root = etree.fromstring(xml, V.PARSER)
    n = len(root.find(V.Q + "blocks").findall(V.Q + "block")) - 1      # top-level blocks minus the info chain
    assert n >= 1
    assert V.placeholder_lint(xml, n, e["statut"]) == []
    assert V.placeholder_lint(xml, n + 1, e["statut"])      # a missing placeholder is detected
    assert e["statut"] == "partiel"


def test_placeholder_comment_has_rule_and_hash(conv):
    e, xml = conv("\\title{T}\n\\statement{x}\n\\wims{y=1}\n\\answer{p}{1}{type=numeric}\n")
    assert b"TODO[OEF2XML" in xml and b"sha256=" in xml
