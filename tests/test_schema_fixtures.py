"""AC-3 / REQ-ARCH-5: the schema fixtures shipped in validation/ pass unchanged (8/8)."""
import subprocess
import sys

from conftest import ROOT


def test_validation_xml_fixtures():
    r = subprocess.run([sys.executable, str(ROOT / "validation/xml/tests/run_schema_tests.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_oef_validator_unit_tests():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "validation/oef/oef_validate/tests")],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]


def test_catalog_copy_equals_tools_file():
    a = (ROOT / "src/oef2xml/data/xml_block_catalog.json").read_bytes()
    b = (ROOT / "tools/corpus_stats/xml_block_catalog.json").read_bytes()
    assert a == b
