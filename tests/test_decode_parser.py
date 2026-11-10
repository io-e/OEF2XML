import pytest

from oef2xml.decode import DecodeError, decode_bytes, line_col, normalise
from oef2xml.parser import parse


def test_utf8_and_latin1_detection():
    t, enc = decode_bytes("é".encode("utf-8"))
    assert (t, enc) == ("é", "utf-8")
    t, enc = decode_bytes("é".encode("latin-1"))
    assert t == "é" and enc in ("latin-1", "cp1252")


def test_bom_stripped_and_newlines_normalised():
    t, _ = decode_bytes(b"\xef\xbb\xbfa\r\nb\rc")
    assert not t.startswith("\ufeff")
    assert "\r" not in normalise(t)


def test_forced_encoding_error():
    with pytest.raises(DecodeError):
        decode_bytes("é".encode("latin-1"), "utf-8")


def test_line_col_is_one_based():
    assert line_col("ab\ncd", 3) == (2, 1)


def test_parser_blocks():
    r = parse("\\title{T}\n\\statement{x}\n\\answer{p}{1}{type=numeric}\n")
    names = [d.name for d in r.directives]
    assert names[:3] == ["title", "statement", "answer"]
    assert not r.errors


def test_parser_reports_unbalanced():
    r = parse("\\statement{abc\n")
    assert r.errors
