"""REQ-PATH-*: Unicode, spaces and very long paths for input, output and --assets-dir; the gate runs on an ASCII scratch copy."""
import os
import shutil
from pathlib import Path

import pytest

from conftest import SIMPLE

NAMES = ["数学", "Συνάρτηση", "test_😀", "été", "with space", "a" * 120]


def _extended_path(path):
    """Use the Win32 extended-length namespace for test setup/cleanup (REQ-WIN-1)."""
    path = Path(path)
    if os.name != "nt":
        return path
    value = os.path.abspath(str(path))
    if value.startswith("\\\\?\\"):
        return Path(value)
    if value.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + value[2:])
    return Path("\\\\?\\" + value)


def _gate_args():
    from oef2xml.gate import find_oef2wims
    exe = find_oef2wims(None)
    return ["--gate", "oef2wims", "--oef2wims", exe] if exe else ["--gate", "validator"]


@pytest.mark.parametrize("name", NAMES)
def test_unicode_input_output_assets(cli, tmp_path, name):
    d = tmp_path / name
    try:
        (d / "in").mkdir(parents=True)
        source = d / "in" / f"{name}.oef"
        # Fixture creation uses the Windows extended namespace. The converter
        # receives the ordinary path, proving it adds the prefix itself.
        _extended_path(source).write_bytes(SIMPLE.encode())
        assets = d / "assets"
        assets.mkdir()
        r = cli(source, "-o", d / "out", "--assets-dir", assets, *_gate_args())
        assert r.returncode == 0, r.stderr + r.stdout
        assert _extended_path(d / "out" / f"{name}.xml").is_file()
    finally:
        # Remove a possibly >MAX_PATH file before pytest's own temp cleanup.
        shutil.rmtree(_extended_path(d), ignore_errors=True)


def test_long_path_285_chars(cli, tmp_path):
    seg = "d" * 60
    root = tmp_path / "long_input"
    d = root
    while len(str(d / "x.oef")) < 285:
        d = d / seg
    source = d / "x.oef"
    out = tmp_path / "o"
    try:
        _extended_path(d).mkdir(parents=True)
        # Build exactly >= 285 characters in the absolute input path.
        assert len(str(source)) >= 285
        _extended_path(source).write_bytes(SIMPLE.encode())
        r = cli(source, "-o", out, *_gate_args())
        assert r.returncode == 0, r.stderr + r.stdout
        assert (out / "x.xml").exists()
    finally:
        shutil.rmtree(_extended_path(root), ignore_errors=True)


def test_long_output_path_285_chars(cli, tmp_path):
    source_dir = tmp_path / "input"
    source_dir.mkdir()
    source = source_dir / "x.oef"
    source.write_bytes(SIMPLE.encode())
    root = tmp_path / "long_output"
    out = root
    seg = "o" * 60
    while len(str(out / "x.xml")) < 285:
        out = out / seg
    try:
        r = cli(source, "-o", out, *_gate_args())
        assert r.returncode == 0, r.stderr + r.stdout
        assert _extended_path(out / "x.xml").is_file()
    finally:
        shutil.rmtree(_extended_path(root), ignore_errors=True)


def test_unicode_title_and_text_roundtrip_in_xml(conv):
    src = SIMPLE.replace("Test", "Συνάρτηση 数学 😀 été")
    e, xml = conv(src)
    assert "Συνάρτηση 数学 😀 été".encode("utf-8") in xml
