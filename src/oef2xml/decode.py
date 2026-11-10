"""REQ-IN-3 / REQ-IN-4: encoding detection and oef2wims-compatible byte normalisation."""
from __future__ import annotations

ENCODINGS = ("auto", "utf-8", "latin-1", "cp1252")


class DecodeError(Exception):
    pass


def decode_bytes(raw: bytes, mode: str = "auto") -> tuple[str, str]:
    """Return (text, detected_encoding). REQ-IN-3: BOM -> UTF-8; else strict UTF-8;
    else cp1252 (strict) then ISO-8859-1. Deterministic."""
    if mode not in ENCODINGS:
        raise DecodeError(f"unknown encoding {mode!r}")
    if mode == "auto":
        if raw.startswith(b"\xef\xbb\xbf"):
            return raw[3:].decode("utf-8"), "utf-8-bom"
        try:
            return raw.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            pass
        try:
            return raw.decode("cp1252"), "cp1252"
        except UnicodeDecodeError:
            return raw.decode("latin-1"), "latin-1"
    try:
        if mode == "utf-8" and raw.startswith(b"\xef\xbb\xbf"):
            return raw[3:].decode("utf-8"), "utf-8-bom"
        return raw.decode(mode), mode
    except UnicodeDecodeError as e:
        raise DecodeError(f"cannot decode as {mode}: {e}") from e


def normalise(text: str) -> str:
    """REQ-IN-4: oef2wims getinp() replaces CR and bytes 0..6 by spaces (oef2wims.c:143-165)."""
    return "".join(" " if (c == "\r" or ord(c) <= 6) else c for c in text)


def line_col(text: str, pos: int) -> tuple[int, int]:
    line = text.count("\n", 0, pos) + 1
    col = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return line, col
