"""REQ-ARCH-4 / REQ-WIN-1: compiler scratch paths stay ASCII on Windows."""
import pytest

from oef2xml.gate import ascii_scratch_stem


@pytest.mark.parametrize("name", ["数学", "Συνάρτηση", "test_😀", "été", "with space"])
def test_compiler_scratch_stem_is_ascii(name):
    stem = ascii_scratch_stem(name)
    assert stem.isascii()
    assert "/" not in stem and "\\" not in stem


def test_compiler_scratch_stem_preserves_safe_ascii():
    assert ascii_scratch_stem("exercise-01_v2") == "exercise-01_v2"
