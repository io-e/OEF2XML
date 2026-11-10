"""AC-3 / REQ-ARCH-5: the schema fixtures shipped in validation/ pass unchanged (8/8)."""
import os
import re
import subprocess
import sys

from conftest import ROOT


def test_validation_xml_fixtures():
    r = subprocess.run([sys.executable, str(ROOT / "validation/xml/tests/run_schema_tests.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_oef_validator_unit_tests():
    command = [sys.executable, "-m", "pytest", "-q", str(ROOT / "validation/oef/oef_validate/tests")]
    if os.name == "nt":
        # D-08: validation/ stays read-only. Its CLI test splits on ':' and
        # mistakes the Windows drive separator for the line/column separators.
        # Recheck that behavior portably below instead of editing the fixture.
        command.extend(["-k", "not test_cli_exit_codes"])
    r = subprocess.run(command,
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]


def test_oef_validator_cli_exit_codes_portable():
    # Portable equivalent of the read-only validation test_cli_exit_codes:
    # parse the final line/column markers without splitting a Windows drive.
    root = ROOT / "validation/oef/oef_validate"
    cli = root / "oef_validate.py"
    samples = root / "tests/samples"
    ok = subprocess.run([sys.executable, str(cli), str(samples / "ok_minimal.oef")],
                        capture_output=True, text=True)
    ko = subprocess.run([sys.executable, str(cli), str(samples / "no_statement.oef")],
                        capture_output=True, text=True)
    assert ok.returncode == 0 and ko.returncode == 1
    assert re.search(r":1:1: erreur:", ko.stdout)
    strict = subprocess.run([sys.executable, str(cli), "--strict", str(samples / "warnings.oef")],
                            capture_output=True, text=True)
    assert strict.returncode == 1


def test_catalog_copy_equals_tools_file():
    a = (ROOT / "src/oef2xml/data/xml_block_catalog.json").read_bytes()
    b = (ROOT / "tools/corpus_stats/xml_block_catalog.json").read_bytes()
    assert a == b
