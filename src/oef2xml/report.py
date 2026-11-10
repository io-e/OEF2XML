"""Conversion report (4.4): JSON (REQ-REP-1/2) and TSV (REQ-REP-5), exit codes (REQ-REP-6). No timestamps: AC-6."""
from __future__ import annotations

import json
from collections import Counter

from . import __version__

TSV_COLUMNS = ["fichier", "statut", "fidelite", "encodage", "questions_source", "questions_converties",
               "blocs_question_emis", "nb_gaps", "nb_approx", "nb_risque_evaluation", "gate", "compilateur", "validateur", "rng", "xsd", "schematron", "message"]


def summarize(entries: list[dict], meta: dict | None = None) -> dict:
    c = Counter(e["statut"] for e in entries)
    f = Counter(e["fidelite"] for e in entries)
    nt_files: Counter = Counter()
    nt_occ: Counter = Counter()
    ap_occ: Counter = Counter()
    for e in entries:
        for k, v in e["non_traduits"].items():
            nt_files[k] += 1
            nt_occ[k] += v
        for k, v in e["approximations"].items():
            ap_occ[k] += v
    du: Counter = Counter()           # D-18: dropped-unread by cause
    for e in entries:
        for d in e["details"]:
            if d["construct"] == "dropped-unread":
                du[d.get("cause_gap") or "sans_cause"] += 1
    return {
        "version_rapport": 1,
        "outil": f"oef2xml {__version__}",
        "schemas": (meta or {}).get("schemas", {}),
        "compilateur_sha256": (meta or {}).get("compilateur_sha256"),
        "resume": {"complet": c.get("complet", 0), "partiel": c.get("partiel", 0), "echec": c.get("echec", 0),
                   "fichiers": len(entries),
                   "fidelite": {"exacte": f.get("exacte", 0), "approchee": f.get("approchee", 0), "non_verifiee": f.get("non_verifiee", 0), "null": f.get(None, 0)}},
        "fichiers": entries,
        "non_traduits_fichiers": dict(sorted(nt_files.items())),
        "non_traduits_occurrences": dict(sorted(nt_occ.items())),
        "approximations_occurrences": dict(sorted(ap_occ.items())),
        "dropped_unread_causes": dict(sorted(du.items())),
        "options_non_implementees": list((meta or {}).get("options_non_implementees", [])),
    }


def write_json(path, entries: list[dict], meta: dict | None = None) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summarize(entries, meta), fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def tsv_rows(entries: list[dict]):
    yield "\t".join(TSV_COLUMNS)
    for e in entries:
        nb_gaps = sum(e["non_traduits"].values())
        nb_approx = sum(e["approximations"].values())
        vals = [e["source"], e["statut"], "" if e["fidelite"] is None else e["fidelite"], e["encodage"], e["questions_source"], e["questions_converties"],
                e["blocs_question_emis"], nb_gaps, nb_approx, e["nb_risque_evaluation"], e["gate"], e["compilateur"], e["validateur"], e["rng"], e["xsd"], e["schematron"],
                (e["message"] or "").replace("\t", " ").replace("\n", " ")]
        yield "\t".join(str(v) for v in vals)


def write_tsv(path, entries: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in tsv_rows(entries):
            fh.write(row + "\n")


def exit_code(entries: list[dict]) -> int:
    s = {e["statut"] for e in entries}
    if "echec" in s:
        return 2
    if "partiel" in s:
        return 1
    return 0
