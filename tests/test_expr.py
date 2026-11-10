from oef2xml.expr import Str, Var, parse_text_value


def test_undeclared_latex_command_stays_literal():
    out = parse_text_value("x=\\(\\nearrow\\)", set())
    assert out == Str(parts=["x=\\(\\nearrow\\)"])


def test_declared_reference_in_math():
    out = parse_text_value("\\(\\a+1\\)", {"a"})
    assert any(isinstance(p, Var) and p.name == "a" for p in out.parts)
