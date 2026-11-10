"""Compile gate (REQ-ARCH-4): oef2wims on a scratch copy; the input folder is never written to."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

ERR_RE = re.compile(r"^ERROR (.*?) at line (\d+) col (\d+)\.?\s*$", re.M)


def ascii_scratch_stem(name: str) -> str:
    """REQ-ARCH-4 / REQ-WIN-1: keep compiler scratch filenames ASCII-only."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


@dataclass
class GateResult:
    ok: bool
    mode: str                 # oef2wims | validator | none
    message: str = ""
    line: int = 0
    col: int = 0
    rc: int = 0
    timeout: bool = False


def find_oef2wims(explicit: str | None = None) -> str | None:
    cand = explicit or os.environ.get("OEF2XML_OEF2WIMS")
    if cand:
        return cand if Path(cand).exists() else None
    for name in ("oef2wims-v2.exe", "oef2wims-log.exe", "oef2wims"):
        w = shutil.which(name)
        if w:
            return w
    return None


def run_gate(exe: str, name: str, raw: bytes, keep: str | None = None, timeout: int = 60) -> GateResult:
    """copy `raw` to <scratch>/<stem>.oef, run the compiler there, parse its message, delete the scratch files."""
    exe_name = Path(exe).name.lower()
    wrapper = exe_name.endswith(".exe") and "v2" in exe_name
    scratch = tempfile.mkdtemp(prefix="oef2xml_gate_")
    try:
        src = Path(scratch) / (ascii_scratch_stem(name) + ".oef")
        src.write_bytes(raw)
        cmd = [exe] + (["--json"] if wrapper else []) + [str(src)]
        env = dict(os.environ, PYTHONUTF8="1")
        p = subprocess.run(cmd, cwd=scratch, capture_output=True, timeout=timeout, env=env)
        out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
        if p.returncode == 0:
            return GateResult(True, "oef2wims", "", 0, 0, 0)
        m = ERR_RE.search(out)
        if m:
            return GateResult(False, "oef2wims", f"{m.group(1)}", int(m.group(2)), int(m.group(3)), p.returncode)
        out = out.replace(scratch, "<scratch>")
        lines = [l.strip() for l in out.splitlines() if l.strip() and not l.strip().endswith("..")]
        first = re.sub(r"^ERROR ", "", lines[0]) if lines else f"compiler refused the file (exit code {p.returncode})"
        return GateResult(False, "oef2wims", first, 0, 0, p.returncode)
    except subprocess.TimeoutExpired:
        return GateResult(False, "oef2wims", f"compiler timeout after {timeout} s", 0, 0, -1, True)
    finally:
        if keep:
            Path(keep).mkdir(parents=True, exist_ok=True)
            for f in Path(scratch).iterdir():
                shutil.copy2(f, Path(keep) / f.name)
        shutil.rmtree(scratch, ignore_errors=True)


def file_sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()
