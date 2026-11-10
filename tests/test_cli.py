"""CLI contract (section 12): exit codes, output folder rules, report determinism (AC-6), REQ-BATCH-2."""
import json
import os
import shutil

import pytest

from conftest import SIMPLE


def write(p, text=SIMPLE):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return p


def test_exit_0_complet(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef")
    r = cli(f, "-o", tmp_path / "out", "--gate", "validator")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "out" / "a.xml").exists()


def test_exit_1_partiel(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef", "\\title{T}\n\\statement{x}\n")
    r = cli(f, "-o", tmp_path / "out", "--gate", "validator")
    assert r.returncode == 1


def test_exit_2_echec(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef", "\\statement{abc\n")
    r = cli(f, "-o", tmp_path / "out", "--gate", "validator")
    assert r.returncode == 2
    assert not (tmp_path / "out" / "a.xml").exists()      # no XML for echec (REQ-ERR-*)


def test_exit_64_usage(cli, tmp_path):
    assert cli().returncode == 64
    assert cli(tmp_path / "nothing.oef").returncode == 64
    assert cli("--bogus-option").returncode != 0


def test_refuses_to_write_into_input_folder(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef")
    r = cli(f, "-o", tmp_path / "in", "--gate", "validator")
    assert r.returncode == 64
    assert not (tmp_path / "in" / "a.xml").exists()
    r = cli(f, "-o", tmp_path / "in", "--gate", "validator", "--force")
    assert r.returncode == 0 and (tmp_path / "in" / "a.xml").exists()


def test_input_folder_untouched(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef")
    before = sorted(os.listdir(tmp_path / "in"))
    cli(tmp_path / "in", "-o", tmp_path / "out", "--gate", "validator")
    assert sorted(os.listdir(tmp_path / "in")) == before


def test_report_deterministic_across_output_folders(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef")
    write(tmp_path / "in" / "b.oef", "\\title{B}\n\\statement{x}\n")
    for n in ("o1", "o2"):
        cli(tmp_path / "in", "-o", tmp_path / n, "--gate", "validator", "--report", tmp_path / f"{n}.json",
            "--csv", tmp_path / f"{n}.tsv")
    r1, r2 = [json.loads((tmp_path / f"{n}.json").read_text()) for n in ("o1", "o2")]
    for r in (r1, r2):
        for e in r["fichiers"]:
            e["source"] = os.path.basename(e["source"])
    assert r1 == r2
    assert (tmp_path / "o1" / "a.xml").read_bytes() == (tmp_path / "o2" / "a.xml").read_bytes()


def test_jobs_gives_same_result(cli, tmp_path):
    for i in range(5):
        write(tmp_path / "in" / f"f{i}.oef")
    cli(tmp_path / "in", "-o", tmp_path / "o1", "--gate", "validator", "--jobs", "1")
    cli(tmp_path / "in", "-o", tmp_path / "o2", "--gate", "validator", "--jobs", "3")
    for i in range(5):
        assert (tmp_path / "o1" / f"f{i}.xml").read_bytes() == (tmp_path / "o2" / f"f{i}.xml").read_bytes()


def test_recursive_and_name_collision(cli, tmp_path):
    write(tmp_path / "in" / "x" / "a.oef")
    write(tmp_path / "in" / "y" / "a.oef")
    r = cli(tmp_path / "in", "-r", "-o", tmp_path / "out", "--gate", "validator")
    assert r.returncode == 0
    assert {p.name for p in (tmp_path / "out").glob("*.xml")} == {"a.xml", "a_2.xml"}


def test_report_fields_req_rep_2(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef")
    cli(f, "-o", tmp_path / "out", "--gate", "validator", "--report", tmp_path / "r.json")
    e = json.loads((tmp_path / "r.json").read_text())["fichiers"][0]
    for k in ("source", "sortie", "id", "titre", "statut", "fidelite", "questions_source", "questions_converties",
              "questions_gap", "questions_taint", "blocs_question_emis", "directives_source", "gaps", "details"):
        assert k in e, k


def test_dump_modes(cli, tmp_path):
    f = write(tmp_path / "in" / "a.oef")
    assert "variables_set" in cli(f, "--dump").stdout
    assert json.loads(cli(f, "--dump-ir").stdout)["id"]


def test_no_gate_leftovers_in_tmp(cli, tmp_path):
    from oef2xml.gate import find_oef2wims
    exe = find_oef2wims(None)
    if not exe:
        pytest.skip("oef2wims not available")
    f = write(tmp_path / "in" / "a.oef")
    before = set(os.listdir("/tmp"))
    r = cli(f, "-o", tmp_path / "out", "--gate", "oef2wims", "--oef2wims", exe)
    assert r.returncode == 0, r.stderr
    leftovers = {n for n in set(os.listdir("/tmp")) - before if "oef2" in n.lower()}
    assert not leftovers
