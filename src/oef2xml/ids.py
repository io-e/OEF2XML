"""REQ-OUT-3: deterministic Blockly-style ids = sha1(program id + structural path), 20 chars."""
import hashlib

ALPHABET = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            "!#$%()*+,-./:;=?@[]^_`{|}~")


def make_id(program_id: str, path: str) -> str:
    d = hashlib.sha1(f"{program_id}\x00{path}".encode("utf-8")).digest()
    n = int.from_bytes(d, "big")
    out = []
    for _ in range(20):
        n, r = divmod(n, len(ALPHABET))
        out.append(ALPHABET[r])
    return "".join(out)
