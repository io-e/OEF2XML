# MVP gate (spec 14.2) and acceptance checks

Files: 1433; CLI exit code of the run: 2; `--trig-units`: (none)

## MVP gate numbers

| Metric | Measured | Threshold | Result |
|---|---:|---:|---|
| H: M1 files with Q ≥ 1 | 4 of 5 | ≥ 4 | PASS |
| Gn: M1 files with Q ≥ 1 | 219 of 324 | ≥ 260 | FAIL |
| Gn: M1 files that have ≥ 1 source `\answer`/`\choice` (upper bound of the line above) | 223 | ≥ 260 needed | UNREACHABLE for any tool |
| Gn: echec | 0 (0.0 %) | ≤ 1 % | PASS |
| crash | 0 | 0 | PASS |
| M files accounted for in the report | 212 | 212 | PASS |
| DIFF-SILENT (RT-A) | 3 | 0 | FAIL |

MVP pass as written: **False**

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
  "non_verifiee": 528,
  "approchee": 905
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
  "compilateur",
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
  "DIFF-EXPLAINED": 1095,
  "IDENTICAL": 2,
  "DIFF-SILENT": 3
 },
 "diff_silent": 3,
 "files_without_o2": [],
 "marker_lines_not_equal_to_G22_reports": 0,
 "examples_silent": [
  {
   "file": "01019.oef",
   "hunks": [
    {
     "tag": "delete",
     "o1": [
      "\\real{b1=evalue(\\exp_left_init,x=0)}",
      "\\real{b2=evalue(\\exp_right_init,x=0)}",
      "\\real{x2o10=evalue(\\exp_left_init,x=1)}",
      "\\real{a1=(\\x2o10-\\b1)}",
      "\\real{x2o11=evalue(\\exp_right_init,x=1)}",
      "\\real{a2=(\\x2o11-\\b2)}",
      "\\num{i=0}",
      "\\while{(\\a1 > 0)}[\\text{graphique_x=\\graphique} \\real{abs_x=(-8.25-(0.75*(-(1^(2*\\i)))))} \\real{ord_x=(1.5*floor(\\i))} \\if{(\\a1 >= 1)}[\\num{x2o12=1}]else[\\text{x2o12=\\a1}] \\text{taille_x=\\x2o12} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{a1=(\\a1-1)}]",
      "\\num{i=0}",
      "\\while{(\\a2 > 0)}[\\text{graphique_x=\\graphique} \\real{abs_x=(3.75-(0.75*(-(1^(2*\\i)))))} \\real{ord_x=(1.5*floor(\\i))} \\if{(\\a2 >= 1)}[\\num{x2o13=1}]else[\\text{x2o13=\\a2}] \\text{taille_x=\\x2o13} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{a2=(\\a2-1)}]",
      "\\num{i=0}",
      "\\while{(\\b1 > 0)}[\\text{graphique_1=\\graphique} \\real{abs_1=(-4.5-(0.5*(-(1^(2*\\i)))))} \\num{ord_1=(2*floor(\\i))} \\if{(\\b1 >= 1)}[\\num{x2o14=1}]else[\\text{x2o14=\\b1}] \\text{taille_1=\\x2o14} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{b1=(\\b1-1)}]",
      "\\num{i=0}",
      "\\while{(\\b2 > 0)}[\\text{graphique_1=\\graphique} \\real{abs_1=(7.5-(0.5*(-(1^(2*\\i)))))} \\num{ord_1=(2*floor(\\i))} \\if{(\\b2 >= 1)}[\\num{x2o15=1}]else[\\text{x2o15=\\b2}] \\text{taille_1=\\x2o15} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{b2=(\\b2-1)}]",
      "\\text{x2o16=\\a,\\ap}",
      "\\text{x2o17=wims(sort numeric items \\x2o16)}",
      "\\text{x2o18=\\x2o17[1]}",
      "\\statement{<div style=\"text-align:center\">\\graphique</div><div style=\"text-align:center\">\\(\\boxed{\\exp_left_init=\\exp_right_init}\\)</div><br>Pour commencer, quelle manipulation doit-on faire pour qu'il ne reste des éléments \\(\\fcolorbox{blue}{CarnationPink}{$x$}\\) que sur un seul des deux plateaux de la balance ?<div class=\"x2o_q\">\\embed{reply1}</div><div class=\"x2o_q\">\\embed{reply2}</div><div class=\"x2o_q\">question \\embed{reply3}</div><div class=\"x2o_q\">\\embed{reply4}</div><div class=\"x2o_q\">\\embed{reply5}</div>→ Il faut retirer \\reply1 éléments \\(\\fcolorbox{blue}{CarnationPink}{$x$}\\) sur chaque plateau.}",
      "\\real{solution_v=(rint((((\\bp-\\b)/(\\a-\\ap))*(10^\\nb_decimales)))/(10^\\nb_decimales))}",
      "\\real{x2o19=((\\a*\\solution_v)+\\b)}",
      "\\real{x2o20=((\\ap*\\solution_v)+\\bp)}",
      "\\text{x2o21=\\a,\\ap}",
      "\\text{x2o22=wims(sort numeric items \\x2o21)}",
      "\\text{x2o23=\\x2o22[1]}",
      "\\real{x2o24=(rint((((\\a-\\x2o23)/abs((\\a-\\ap)))*(10^\\nb_decimales)))/(10^\\nb_decimales))}",
      "\\text{x2o25=\\b,\\bp}",
      "\\text{x2o26=wims(sort numeric items \\x2o25)}",
      "\\text{x2o27=\\x2o26[1]}",
      "\\real{x2o28=(rint((((\\b-\\x2o27)/abs((\\a-\\ap)))*(10^\\nb_decimales)))/(10^\\nb_decimales))}",
      "\\text{exp_left_temp=\\x2o24*x+\\x2o28}",
      "\\text{x2o29=\\a,\\ap}",
      "\\text{x2o30=wims(sort numeric items \\x2o29)}",
      "\\text{x2o31=\\x2o30[1]}",
      "\\real{x2o32=(rint((((\\ap-\\x2o31)/abs((\\a-\\ap)))*(10^\\nb_decimales)))/(10^\\nb_decimales))}",
      "\\text{x2o33=\\b,\\bp}",
      "\\text{x2o34=wims(sort numeric items \\x2o33)}",
      "\\text{x2o35=\\x2o34[1]}",
      "\\real{x2o36=(rint((((\\bp-\\x2o35)/abs((\\a-\\ap)))*(10^\\nb_decimales)))/(10^\\nb_decimales))}",
      "\\text{exp_right_temp=\\x2o32*x+\\x2o36}",
      "\\real{x2o37=abs((\\a-\\ap))}",
      "\\text{graphique=\\graph4}",
      "\\text{exp_left_init=\\exp_left_temp}",
      "\\text{exp_right_init=\\exp_right_temp}",
      "\\real{b1=evalue(\\exp_left_init,x=0)}",
      "\\real{b2=evalue(\\exp_right_init,x=0)}",
      "\\real{x2o38=evalue(\\exp_left_init,x=1)}",
      "\\real{a1=(\\x2o38-\\b1)}",
      "\\real{x2o39=evalue(\\exp_right_init,x=1)}",
      "\\real{a2=(\\x2o39-\\b2)}"
     ],
     "o2": [],
     "explained": false,
     "o1_lines": [
      82,
      237
     ]
    }
   ]
  },
  {
   "file": "01049.oef",
   "hunks": [
    {
     "tag": "delete",
     "o1": [
      "\\real{b1=evalue(\\exp_left_init,x=0)}",
      "\\real{b2=evalue(\\exp_right_init,x=0)}",
      "\\real{x2o10=evalue(\\exp_left_init,x=1)}",
      "\\real{a1=(\\x2o10-\\b1)}",
      "\\real{x2o11=evalue(\\exp_right_init,x=1)}",
      "\\real{a2=(\\x2o11-\\b2)}",
      "\\num{i=0}",
      "\\while{(\\a1 > 0)}[\\text{graphique_x=\\graphique} \\real{abs_x=(-8.25-(0.75*(-(1^(2*\\i)))))} \\real{ord_x=(1.5*floor(\\i))} \\if{(\\a1 >= 1)}[\\num{x2o12=1}]else[\\text{x2o12=\\a1}] \\text{taille_x=\\x2o12} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{a1=(\\a1-1)}]",
      "\\num{i=0}",
      "\\while{(\\a2 > 0)}[\\text{graphique_x=\\graphique} \\real{abs_x=(3.75-(0.75*(-(1^(2*\\i)))))} \\real{ord_x=(1.5*floor(\\i))} \\if{(\\a2 >= 1)}[\\num{x2o13=1}]else[\\text{x2o13=\\a2}] \\text{taille_x=\\x2o13} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{a2=(\\a2-1)}]",
      "\\num{i=0}",
      "\\while{(\\b1 > 0)}[\\text{graphique_1=\\graphique} \\real{abs_1=(-4.5-(0.5*(-(1^(2*\\i)))))} \\num{ord_1=(2*floor(\\i))} \\if{(\\b1 >= 1)}[\\num{x2o14=1}]else[\\text{x2o14=\\b1}] \\text{taille_1=\\x2o14} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{b1=(\\b1-1)}]",
      "\\num{i=0}",
      "\\while{(\\b2 > 0)}[\\text{graphique_1=\\graphique} \\real{abs_1=(7.5-(0.5*(-(1^(2*\\i)))))} \\num{ord_1=(2*floor(\\i))} \\if{(\\b2 >= 1)}[\\num{x2o15=1}]else[\\text{x2o15=\\b2}] \\text{taille_1=\\x2o15} \\text{centre=«non traduit : point»} \\real{i=(\\i+0.5)} \\real{b2=(\\b2-1)}]",
      "\\text{x2o16
```
