# MVP gate (spec 14.2) and acceptance checks

Files: 1433; CLI exit code of the run: 2; `--trig-units`: (none)

## MVP gate numbers

| Metric | Measured | Threshold | Result |
|---|---:|---:|---|
| H: M1 files with Q ≥ 1 (80 % of the 5 that have a source question) | 4 of 5 | ≥ 4 | PASS |
| Gn: M1 files with Q ≥ 1 (80 % of the 223 that have a source question) | 219 of 324 | ≥ 179 | PASS |
| Gn: M1 files that have ≥ 1 source `\answer`/`\choice` (upper bound of the line above) | 223 | ≥ 179 needed | reachable |
| Gn: echec | 0 (0.0 %) | ≤ 1 % | PASS |
| crash | 0 | 0 | PASS |
| M files accounted for in the report | 212 | 212 | PASS |
| DIFF-SILENT (RT-A) | 0 | 0 | PASS |

MVP pass as written: **True**

## Per corpus

- H: {'N': 121, 'partiel': 119, 'Q': 31, 'complet': 2}
- M: {'N': 212, 'partiel': 210, 'Q': 6, 'echec': 2}
- Gn: {'N': 1100, 'complet': 124, 'Q': 489, 'partiel': 976}

## AC-1

```
{
 "files": 1433,
 "divergences_parser_vs_compiler": 0,
 "examples": []
}
```

## AC-2

```
{
 "compiler_refusals": [
  "00286.oef",
  "00307.oef"
 ],
 "all_reported_echec_without_xml": true,
 "expected": [
  "00286.oef",
  "00307.oef"
 ]
}
```

## AC-3

```
{
 "run_schema_tests_exit": 0,
 "written": 1431,
 "rng_ok": 1431,
 "xsd_ok": 1431
}
```

## AC-5

```
{
 "files_linted": 1431,
 "violations": 0,
 "examples": [],
 "types_used": 31,
 "outside_whitelist": []
}
```

## AC-6

```
{
 "files": 2864,
 "same_file_set": true,
 "different_files": 0,
 "report_json_identical": true,
 "report_tsv_identical": true,
 "examples": []
}
```

## AC-7

```
{
 "I1_I2_violations": 0,
 "I3_violations": 0,
 "examples": []
}
```

## AC-8

```
{
 "complet_with_placeholder_dynamic_G22_or_trig": 0,
 "examples": [],
 "placeholder_lint_failures_on_all_written": 0,
 "examples_lint": []
}
```

## AC-11

```
{
 "input_folder_unchanged": true,
 "outputs_outside_input_folder": true,
 "note": "Unicode path suite: tests/test_unicode_paths.py"
}
```

## AC-12

```
{
 "entries_missing_fields": 0,
 "fidelite_values": {
  "non_verifiee": 518,
  "approchee": 915
 },
 "exacte": 0,
 "tsv_columns": [
  "fichier",
  "statut",
  "fidelite",
  "encodage",
  "questions_source",
  "questions_converties",
  "blocs_question_emis",
  "nb_gaps",
  "nb_approx",
  "nb_risque_evaluation",
  "gate",
  "compilateur",
  "validateur",
  "rng",
  "xsd",
  "schematron",
  "message"
 ],
 "exit_code_run": 2,
 "exit_codes_tested_in": "tests/test_cli.py"
}
```

## RT-A

```
{
 "run": true,
 "files": 1100,
 "verdicts": {
  "DIFF-EXPLAINED": 1098,
  "IDENTICAL": 2
 },
 "diff_silent": 0,
 "files_without_o2": [],
 "marker_lines_not_equal_to_G22_reports": 0,
 "examples_silent": [],
 "p1_sample": {
  "list": "tests/data/rta_p1_sample.txt",
  "files": 100,
  "verdicts": {
   "DIFF-EXPLAINED": 100
  },
  "diff_silent": 0
 }
}
```
