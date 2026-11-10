"""REQ-PATH-*: Unicode, spaces and very long paths for input, output and --assets-dir; the gate runs on an ASCII scratch copy."""
import os
import shutil

import pytest

from conftest import SIMPLE

NAMES = ["数学", "Συνάρτηση", "test_😀", "été", "with space", "a" * 120]


def _gate_args():
    from oef2xml.gate import find_oef2wims
    exe = find_oef2wims(None)
    return ["--gate", "oef2wims", "--oef2wims", exe] if exe else ["--gate", "validator"]


@pytest.mark.parametrize("name", NAMES)
def test_unicode_input_output_assets(cli, tmp_path, name):
    d = tmp_path / name
    (d / "in").mkdir(parents=True)
    (d / "in" / f"{name}.oef").write_bytes(SIMPLE.encode())
    assets = d / "assets"
    assets.mkdir()
    r = cli(d / "in" / f"{name}.oef", "-o", d / "out", "--assets-dir", assets, *_gate_args())
    assert r.returncode == 0, r.stderr + r.stdout
    assert (d / "out" / f"{name}.xml").exists()


def test_long_path_285_chars(cli, tmp_path):
    seg = "d" * 60
    d = tmp_path
    while len(str(d / "x.oef")) < 285:
        d = d / seg
    d.mkdir(parents=True)
    # build exactly >= 285 characters in the absolute input path
    assert len(str(d / "x.oef")) >= 285
    (d / "x.oef").write_bytes(SIMPLE.encode())
    out = tmp_path / "o"
    r = cli(d / "x.oef", "-o", out, *_gate_args())
    assert r.returncode == 0, r.stderr + r.stdout
    assert (out / "x.xml").exists()


def test_unicode_title_and_text_roundtrip_in_xml(conv):
    src = SIMPLE.replace("Test", "Συνάρτηση 数学 😀 été")
    e, xml = conv(src)
    assert "Συνάρτηση 数学 😀 été".encode("utf-8") in xml
