"""D-16 / AC-8: the committed, fixed RT-A sample (tests/data/rta_p1_sample.txt) has 0 DIFF-SILENT.
Needs the Go forward converter and the corpus: set OEF2XML_XML2OEF=/path/to/xml2oef and OEF2XML_CORPUS=/path/to/corpus (skipped, and
reported as skipped, when absent)."""
import json
import os
import sys
from pathlib import Path

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
SAMPLE = ROOT / "tests" / "data" / "rta_p1_sample.txt"


def sample_files():
    return [ln.strip() for ln in SAMPLE.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]


def test_sample_list_is_fixed_and_well_formed():
    fs = sample_files()
    assert len(fs) == 100 and len(set(fs)) == 100 and fs == sorted(fs)
    assert all(f.endswith(".oef") for f in fs)


def test_rta_sample_has_no_diff_silent(cli, tmp_path):
    x2o, corpus = os.environ.get("OEF2XML_XML2OEF"), os.environ.get("OEF2XML_CORPUS")
    if not (x2o and corpus and Path(x2o).exists() and Path(corpus).is_dir()):
        pytest.skip("OEF2XML_XML2OEF / OEF2XML_CORPUS not set: RT-A sample not run")
    import roundtrip as RT
    inp = tmp_path / "in"
    inp.mkdir()
    for f in sample_files():
        os.symlink(Path(corpus) / f, inp / f)
    rep = tmp_path / "r.json"
    cli(inp, "-o", tmp_path / "x", "--gate", "none", "--report", rep)
    entries = {Path(e["source"]).name: e for e in json.loads(rep.read_text(encoding="utf-8"))["fichiers"]}
    xs = [tmp_path / "x" / e["sortie"] for e in entries.values() if e["sortie"]]
    RT.run_forward(x2o, tmp_path / "x", tmp_path / "o2", xs)
    silent = []
    for f, e in entries.items():
        o2 = tmp_path / "o2" / (Path(e["sortie"]).stem + ".oef")
        v = RT.compare(RT.read(Path(corpus) / f), RT.read(o2), e["details"]) if e["sortie"] and o2.exists() else {"verdict": "NO-O2"}
        if v["verdict"] in ("DIFF-SILENT", "NO-O2"):
            silent.append(f)
    assert silent == []
