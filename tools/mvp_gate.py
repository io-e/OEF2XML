#!/usr/bin/env python3
"""MVP gate (spec 14.2, end of phase 1) and acceptance checks AC-1..AC-8, AC-11, AC-12 on the corpus.

Runs the real CLI twice (AC-6), reads the written reports and XML, runs RT-A against the forward converter, and writes
reports/mvp_gate.json + reports/mvp_gate.md. Thresholds are the ones of the spec; nothing is adjusted here.

  python3 tools/mvp_gate.py --corpus /workspace/oefc/corpus --oef2wims /path/to/oef2wims --xml2oef /path/to/xml2oef
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))
import roundtrip as RT  # noqa: E402
from oef2xml import validate as V  # noqa: E402
from oef2xml.shape import catalog  # noqa: E402

TRIG = re.compile(r"(?<![A-Za-z0-9_])(sin|cos|tan|asin|acos|atan|arcsin|arccos|arctan)\s*\(")


def load_tier():
    spec = importlib.util.spec_from_file_location("ocs", ROOT / "tools/corpus_stats/oef_corpus_stats.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.tier_ok


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cli(stage: Path, out: Path, report: Path, tsv: Path, oef2wims: str, extra: list[str]):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
    cmd = [sys.executable, "-m", "oef2xml", "-q", "-o", str(out), "--report", str(report), "--csv", str(tsv),
           "--oef2wims", oef2wims] + extra + [str(stage)]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return p.returncode, p.stderr


def main():
    # REQ-WIN-2: the Markdown report contains Unicode symbols (for example ÔëÑ).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="/workspace/oefc/corpus")
    ap.add_argument("--per-file", default=str(ROOT / "tools/corpus_stats/data/per_file.csv"))
    ap.add_argument("--oef2wims", required=True)
    ap.add_argument("--xml2oef", default="")
    ap.add_argument("--out", default=str(ROOT / "reports"))
    ap.add_argument("--work", default="")
    ap.add_argument("--trig-units", default=None)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    tier_ok = load_tier()
    rows = list(csv.DictReader(open(a.per_file, encoding="utf-8")))
    corpus = Path(a.corpus)
    work = Path(a.work or tempfile.mkdtemp(prefix="mvp_gate_"))
    work.mkdir(parents=True, exist_ok=True)
    stage = work / "in"
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir()
    for r in rows:
        src, dst = corpus / r["file"], stage / r["file"]
        try:
            os.symlink(src, dst)
        except (OSError, NotImplementedError):
            # Windows may disable the symlink privilege. An isolated copy is
            # equivalent for the gate and protects the source corpus (D-19).
            shutil.copy2(src, dst)
    before = sorted(os.listdir(corpus))
    extra = ["--trig-units", a.trig_units] if a.trig_units else []
    runs = []
    for k in ("A", "B"):
        out, rep, tsv = work / f"out{k}", work / f"report{k}.json", work / f"report{k}.tsv"
        shutil.rmtree(out, ignore_errors=True)
        rc, err = run_cli(stage, out, rep, tsv, a.oef2wims, extra)
        runs.append((rc, out, rep, tsv, err))
    rcA, outA, repA, tsvA, errA = runs[0]
    report = json.loads(repA.read_text(encoding="utf-8"))
    entries = {Path(e["source"]).name: e for e in report["fichiers"]}
    origin = {r["file"]: r["origin"] for r in rows}
    group = lambda f: "H" if origin[f] in ("upstream_class", "upstream_module") else ("M" if origin[f] == "upstream_model" else "Gn")
    res: dict = {"corpus_files": len(rows), "cli_exit_code": rcA, "trig_units": a.trig_units or "(none)"}

    # --- counts per corpus
    per = {g: Counter() for g in ("H", "M", "Gn")}
    for f, e in entries.items():
        g = group(f)
        per[g]["N"] += 1
        per[g][e["statut"]] += 1
        per[g]["Q"] += e["questions_converties"] >= 1
    res["corpora"] = {g: dict(c) for g, c in per.items()}

    # --- MVP gate (14.2)
    m1 = [r["file"] for r in rows if tier_ok(set(r["features"].split(";")))]
    mv = {"M1_files": Counter(group(f) for f in m1)}
    hq = sum(entries[f]["questions_converties"] >= 1 for f in m1 if group(f) == "H")
    gq = sum(entries[f]["questions_converties"] >= 1 for f in m1 if group(f) == "Gn")
    h_n, g_n = mv["M1_files"]["H"], mv["M1_files"]["Gn"]
    g_with_answer = sum(1 for f in m1 if group(f) == "Gn" and entries[f]["questions_source"] >= 1)
    h_with_answer = sum(1 for f in m1 if group(f) == "H" and entries[f]["questions_source"] >= 1)
    # D-15: threshold = 80 % of the M1 files whose source has \answer or \choice, computed here, never hard-coded
    h_thr, g_thr = -(-4 * h_with_answer // 5), -(-4 * g_with_answer // 5)
    gn_echec = per["Gn"]["echec"]
    crash = sum("crash" in e["flags"] for e in entries.values())
    m_files = [f for f in entries if group(f) == "M"]
    mv.update({
        "H_Q>=1": hq, "H_M1": h_n, "H_M1_with_question": h_with_answer, "H_threshold": h_thr,
        "Gn_Q>=1": gq, "Gn_M1": g_n, "Gn_threshold": g_thr,
        "Gn_M1_with_at_least_one_source_question": g_with_answer,
        "Gn_threshold_reachable": g_with_answer >= g_thr,
        "Gn_echec": gn_echec, "Gn_echec_pct": round(100.0 * gn_echec / max(1, per["Gn"]["N"]), 2), "Gn_echec_max_pct": 1.0,
        "crash": crash, "M_files_accounted": len(m_files), "M_files_expected": 212,
    })
    res["mvp"] = mv

    # --- AC-1 / AC-2 : parser vs compile gate
    div = [f for f, e in entries.items() if "divergence_parser_compilateur" in e["flags"]]
    refused = sorted(f for f, e in entries.items() if e["compilateur"] == "ko")
    res["AC-1"] = {"files": len(entries), "divergences_parser_vs_compiler": len(div), "examples": div[:5]}
    res["AC-2"] = {"compiler_refusals": refused,
                   "all_reported_echec_without_xml": all(entries[f]["statut"] == "echec" and entries[f]["sortie"] is None for f in refused),
                   "expected": ["00286.oef", "00307.oef"]}

    # --- AC-3 schemas
    p = subprocess.run([sys.executable, str(ROOT / "validation/xml/tests/run_schema_tests.py")], capture_output=True, text=True)
    written = [e for e in entries.values() if e["statut"] != "echec"]
    res["AC-3"] = {"run_schema_tests_exit": p.returncode,
                   "written": len(written), "rng_ok": sum(e["rng"] == "ok" for e in written), "xsd_ok": sum(e["xsd"] == "ok" for e in written)}

    # --- AC-5 shape lint + AC-7 invariants + AC-8
    sd = str(V.default_schema_dir())
    lint_bad, inv_bad, i3_bad, ph_bad, complet_bad, types_used = [], [], [], [], [], Counter()
    from lxml import etree
    for f, e in entries.items():
        if e["statut"] == "echec":
            continue
        xmlp = outA / e["sortie"]
        xml = xmlp.read_bytes()
        pb = V.shape_lint(xml, sd)
        if pb:
            lint_bad.append((f, pb[0]))
        for b in etree.fromstring(xml, V.PARSER).iter(V.Q + "block", V.Q + "shadow"):
            types_used[b.get("type")] += 1
        if e["questions_source"] != e["questions_converties"] + e["questions_gap"] + e["questions_taint"]:
            inv_bad.append((f, "I2"))
        if e["directives_source"] != e["directives_traduites"] + e["directives_approximees"] + e["directives_info"] + e["directives_non_traduites"]:
            inv_bad.append((f, "I1"))
        if V.count_question_blocks(xml) != e["blocs_question_emis"] or e["blocs_question_emis"] != e["questions_converties"]:
            i3_bad.append(f)
        nph = sum(e["non_traduits"].values())
        if V.placeholder_lint(xml, nph, e["statut"]):
            ph_bad.append(f)
        if e["statut"] == "complet":
            src = (corpus / f).read_bytes().decode("latin-1")
            if nph or "type_dynamique" in e["flags"] or "G-22" in e["gaps"] or "aucune_question" in e["flags"] \
                    or (not a.trig_units and TRIG.search(re.sub(r"%%[^\n]*", "", src))):
                complet_bad.append(f)
    wl = V.whitelist(sd)
    res["AC-5"] = {"files_linted": len(written), "violations": len(lint_bad), "examples": lint_bad[:5],
                   "types_used": len(types_used), "outside_whitelist": sorted(t for t in types_used if t not in wl)}
    res["AC-7"] = {"I1_I2_violations": len(inv_bad), "I3_violations": len(i3_bad), "examples": (inv_bad + i3_bad)[:5]}
    du = Counter()
    for e in entries.values():
        for x in e["details"]:
            if x["construct"] == "dropped-unread":
                du["unread-in-source" if x.get("cause_gap") == "unread-in-source" else ("gap" if x.get("cause_gap") else "sans_cause")] += 1
    res["AC-8"] = {"dropped_unread": {"cause_gap=<gap id>": du["gap"], "cause_gap=unread-in-source": du["unread-in-source"],
                                      "uncaused (count as DIFF-SILENT if a round-trip hunk depends on them)": du["sans_cause"]},
                   "complet_with_placeholder_dynamic_G22_or_trig": len(complet_bad), "examples": complet_bad[:5],
                   "placeholder_lint_failures_on_all_written": len(ph_bad), "examples_lint": ph_bad[:5]}

    # --- AC-6 determinism
    rcB, outB, repB, tsvB, errB = runs[1]
    names = sorted(p.name for p in outA.iterdir())
    same_names = names == sorted(p.name for p in outB.iterdir())
    diff_files = [n for n in names if same_names and sha(outA / n) != sha(outB / n)]
    res["AC-6"] = {"files": len(names), "same_file_set": same_names, "different_files": len(diff_files),
                   "report_json_identical": sha(repA) == sha(repB), "report_tsv_identical": sha(tsvA) == sha(tsvB), "examples": diff_files[:5]}

    # --- AC-11 (gate part) : the input folder is untouched
    # D-19: the Unicode suite counts only on Windows 11; a Linux run is `linux-only`, the status is `pending-windows`
    pu = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests/test_unicode_paths.py")], capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), cwd=str(ROOT))
    unicode_ok = pu.returncode == 0
    if sys.platform == "win32":
        ac11 = "pass" if unicode_ok and before == sorted(os.listdir(corpus)) else "fail"
    else:
        ac11 = "pending-windows"
    res["AC-11"] = {"statut": ac11, "input_folder_unchanged": before == sorted(os.listdir(corpus)),
                    "outputs_outside_input_folder": True,
                    "unicode_suite": "pass" if sys.platform == "win32" and unicode_ok else ("linux-only" if unicode_ok else "fail"),
                    "unicode_suite_platform": sys.platform,
                    "note": "D-19: must be `pass` on Windows 11 before P2 ends; tests/test_unicode_paths.py"}

    # --- AC-12 (gate part)
    need = ["source", "sortie", "id", "titre", "statut", "fidelite", "questions_source", "questions_converties", "questions_gap",
            "questions_taint", "blocs_question_emis", "directives_source", "directives_traduites", "directives_approximees",
            "directives_info", "directives_non_traduites", "non_traduits", "approximations", "encodage", "octets", "details"]
    missing = [f for f, e in entries.items() if any(k not in e for k in need)]
    header = open(tsvA, encoding="utf-8").readline().rstrip("\n").split("\t")
    res["AC-12"] = {"entries_missing_fields": len(missing), "fidelite_values": dict(Counter(e["fidelite"] for e in entries.values())),
                    "exacte": sum(e["fidelite"] == "exacte" for e in entries.values()),
                    "tsv_columns": header, "exit_code_run": rcA, "exit_codes_tested_in": "tests/test_cli.py"}

    # --- RT-A (generated corpus) against the forward converter
    rta = {"run": False}
    if a.xml2oef and Path(a.xml2oef).exists():
        gen = [f for f, e in entries.items() if group(f) == "Gn" and e["statut"] != "echec"]
        xdir = work / "rt_x"
        odir = work / "rt_o2"
        shutil.rmtree(xdir, ignore_errors=True)
        shutil.rmtree(odir, ignore_errors=True)
        xdir.mkdir()
        for f in gen:
            shutil.copy(outA / entries[f]["sortie"], xdir / entries[f]["sortie"])
        RT.run_forward(a.xml2oef, xdir, odir, sorted(xdir.glob("*.xml")))
        verdicts = Counter()
        per_file_verdict = {}
        silent, marker_mismatch, no_o2, ex_silent = [], [], [], []
        for f in gen:
            e = entries[f]
            o2p = odir / (Path(e["sortie"]).stem + ".oef")
            if not o2p.exists():
                no_o2.append(f)
                verdicts["NO-O2"] += 1
                continue
            r = RT.compare(RT.read(corpus / f), RT.read(o2p), e["details"])
            verdicts[r["verdict"]] += 1
            per_file_verdict[f] = r["verdict"]
            if r["verdict"] == "DIFF-SILENT":
                silent.append(f)
                if len(ex_silent) < 12:
                    ex_silent.append({"file": f, "hunks": [h for h in r["hunks"] if not h["explained"]][:2]})
            if r["markers_o1"] != e["gaps"].get("G-22", 0):
                marker_mismatch.append(f)
        rta = {"run": True, "files": len(gen), "verdicts": dict(verdicts), "diff_silent": len(silent), "files_without_o2": no_o2[:10],
               "marker_lines_not_equal_to_G22_reports": len(marker_mismatch), "examples_silent": ex_silent,
               "diff_silent_files": silent}
        sample = [ln.strip() for ln in (ROOT / "tests/data/rta_p1_sample.txt").read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.startswith("#")]
        sv = Counter(per_file_verdict.get(f, "NOT-RUN") for f in sample)
        rta["p1_sample"] = {"list": "tests/data/rta_p1_sample.txt", "files": len(sample), "verdicts": dict(sv),
                            "diff_silent": sv.get("DIFF-SILENT", 0) + sv.get("NOT-RUN", 0)}
    res["RT-A"] = rta

    # --- verdict lines
    mv["H_pass"] = hq >= h_thr
    mv["Gn_pass_as_written"] = gq >= g_thr
    mv["Gn_echec_pass"] = mv["Gn_echec_pct"] <= 1.0
    mv["M_accounting_pass"] = len(m_files) == 212
    mv["diff_silent"] = rta.get("diff_silent", "RT-A not run")
    res["mvp_pass_as_written"] = bool(mv["H_pass"] and mv["Gn_pass_as_written"] and mv["Gn_echec_pass"] and crash == 0
                                      and mv["M_accounting_pass"] and rta.get("diff_silent", 1) == 0)

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "mvp_gate.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    (out_dir / "mvp_gate.md").write_text(render_md(res), encoding="utf-8")
    print(render_md(res))
    if not a.keep and not a.work:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if res["mvp_pass_as_written"] else 1


def render_md(r: dict) -> str:
    mv = r["mvp"]
    L = ["# MVP gate (spec 14.2) and acceptance checks", "",
         f"Files: {r['corpus_files']}; CLI exit code of the run: {r['cli_exit_code']}; `--trig-units`: {r['trig_units']}", "",
         "## MVP gate numbers", "",
         "| Metric | Measured | Threshold | Result |", "|---|---:|---:|---|",
         f"| H: M1 files with Q ≥ 1 (80 % of the {mv['H_M1_with_question']} that have a source question) | {mv['H_Q>=1']} of {mv['H_M1']} | ≥ {mv['H_threshold']} | {'PASS' if mv['H_pass'] else 'FAIL'} |",
         f"| Gn: M1 files with Q ≥ 1 (80 % of the {mv['Gn_M1_with_question'] if 'Gn_M1_with_question' in mv else mv['Gn_M1_with_at_least_one_source_question']} that have a source question) | {mv['Gn_Q>=1']} of {mv['Gn_M1']} | ≥ {mv['Gn_threshold']} | {'PASS' if mv['Gn_pass_as_written'] else 'FAIL'} |",
         f"| Gn: M1 files that have ≥ 1 source `\\answer`/`\\choice` (upper bound of the line above) | {mv['Gn_M1_with_at_least_one_source_question']} | ≥ {mv['Gn_threshold']} needed | {'reachable' if mv['Gn_threshold_reachable'] else 'UNREACHABLE for any tool'} |",
         f"| Gn: echec | {mv['Gn_echec']} ({mv['Gn_echec_pct']} %) | ≤ 1 % | {'PASS' if mv['Gn_echec_pass'] else 'FAIL'} |",
         f"| crash | {mv['crash']} | 0 | {'PASS' if mv['crash'] == 0 else 'FAIL'} |",
         f"| M files accounted for in the report | {mv['M_files_accounted']} | {mv['M_files_expected']} | {'PASS' if mv['M_accounting_pass'] else 'FAIL'} |",
         f"| DIFF-SILENT (RT-A) | {mv['diff_silent']} | 0 | {'PASS' if mv['diff_silent'] == 0 else 'FAIL'} |", "",
         f"MVP pass as written: **{r['mvp_pass_as_written']}**", "", "## Per corpus", ""]
    for g, c in r["corpora"].items():
        L.append(f"- {g}: {c}")
    for k in ("AC-1", "AC-2", "AC-3", "AC-5", "AC-6", "AC-7", "AC-8", "AC-11", "AC-12"):
        v = {a: b for a, b in r[k].items()}
        L += ["", f"## {k}", "", "```", json.dumps(v, ensure_ascii=False, indent=1, default=str), "```"]
    rta = dict(r["RT-A"])
    rta.pop("diff_silent_files", None)
    L += ["", "## RT-A", "", "```", json.dumps(rta, ensure_ascii=False, indent=1, default=str)[:6000], "```", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
