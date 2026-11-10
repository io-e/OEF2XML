"""Shared fixtures. Tests never touch the network; the compile gate is used only when oef2wims is available."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

SIMPLE = """\\title{Test}
\\language{fr}
\\integer{a=randint(2..9)}
\\integer{b=randint(2..9)}
\\statement{Calculez \\a + \\b.}
\\answer{Somme}{\\a+\\b}{type=numeric}
"""


@pytest.fixture
def simple_oef():
    return SIMPLE


def run_cli(*args, cwd=None, env=None):
    e = dict(os.environ)
    e["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + e.get("PYTHONPATH", "")
    if env:
        e.update(env)
    return subprocess.run([sys.executable, "-m", "oef2xml", *map(str, args)], capture_output=True, text=True,
                          cwd=cwd, env=e)


@pytest.fixture
def cli():
    return run_cli


def convert(text, **kw):
    """text -> (entry, xml bytes|None), no gate, validated against RNG+XSD."""
    from oef2xml.convert import Options
    from oef2xml.pipeline import Config, process_bytes
    opts = Options(**kw.pop("opts", {}))
    cfg = Config(gate="none", **kw)
    return process_bytes("t.oef", text.encode("utf-8"), opts, cfg, stem="t")


@pytest.fixture
def conv():
    return convert
