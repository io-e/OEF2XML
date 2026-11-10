"""check_refs.py: finds the specification from any directory, accepts the real spec, and rejects broken copies."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs" / "CAHIER_DES_CHARGES_OEF2XML.md"
TOOL = ROOT / "tools" / "corpus_stats" / "check_refs.py"


def run(*args, cwd=None):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, cwd=cwd)


def mutated(tmp_path, fn):
    p = tmp_path / "spec.md"
    p.write_text(fn(SPEC.read_text(encoding="utf-8")), encoding="utf-8")
    return p


def test_default_path_from_any_cwd(tmp_path):
    r = run(cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "all references resolve" in r.stdout


def test_real_spec_passes():
    assert run(SPEC).returncode == 0


def test_reference_only_mutation_fails(tmp_path):
    # change ONE reference, not a definition: AC-11 cites REQ-ARCH-4
    def f(t):
        i = t.index("| AC-11 |")
        j = t.index("\n", i)
        row = t[i:j]
        assert "REQ-ARCH-4" in row
        return t[:i] + row.replace("REQ-ARCH-4", "REQ-ARCH-44") + t[j:]
    r = run(mutated(tmp_path, f))
    assert r.returncode == 1 and "REQ-ARCH-44" in r.stdout


def test_missing_q_row_fails(tmp_path):
    def f(t):
        return re.sub(r"^\| Q6 \|.*\n", "", t, flags=re.M)
    r = run(mutated(tmp_path, f))
    assert r.returncode != 0


def test_missing_q_template_definition_fails(tmp_path):
    # the heading that defines REQ-MAP-Q-TEMPLATE is renamed: every citation must now be unresolved
    def f(t):
        return t.replace("### 8.3 Question block construction (REQ-MAP-Q-TEMPLATE)", "### 8.3 Question block construction")
    r = run(mutated(tmp_path, f))
    assert r.returncode == 1 and "REQ-MAP-Q-TEMPLATE" in r.stdout


def test_missing_gap_definition_fails(tmp_path):
    def f(t):
        return re.sub(r"^\| G-23 \|.*\n", "", t, flags=re.M)
    assert run(mutated(tmp_path, f)).returncode == 1
