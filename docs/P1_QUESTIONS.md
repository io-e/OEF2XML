# P1 open questions

Rule (owner): an item is listed here only if the spec is silent or contradicts itself on a case, or if an acceptance
criterion cannot be met without changing a requirement. Everything else became a G-nn gap (placeholder + taint,
file `partiel`) and the work went on. Numbers come from `reports/mvp_gate.md` (full corpus, 1433 files).

## Resolved by spec v0.2.6 / DECISIONS.md (no longer open)

- Gn MVP threshold (formerly unreachable): D-15, 80 % of the M1 files with `\answer`/`\choice` (223 -> >= 179), computed by
  `tools/mvp_gate.py`. Measured 219 of 324: PASS.
- AC-8 "0 DIFF-SILENT" in P1: D-16. Fixed by reporting the unread definitions the forward converter drops
  (`dropped-unread`, 01019/01049/01077); the full RT-A run (1100 files) and the committed sample
  `tests/data/rta_p1_sample.txt` (100 files) give 0 DIFF-SILENT.
- RT-A normalisations beyond N1-N8: written into §13.3 as N9-N12 (spec v0.2.6, approved).
- `non_traduits` defined twice: REQ-REP-2/4 disambiguated (`directives_non_traduites` counter + `non_traduits` map).
- Missing gap ids: G-23 (`\feedback`), G-24 (definition directives without mapping), G-25 (text-level control); definitions
  after `\statement` are `info` (§7.1).
- Inverse trigonometry: D-17 (`asin`/`atan` convert the result, `acos` is a gap).

## Still open

1. **G-22 in P1.** AC-8 forbids `complet` for a file with a G-22 marker, but G-22 handling is listed in P2 with idioms,
   and `--idioms off` does not switch G-22 off (REQ-IDIOM-1 is unconditional). G-22 is handled in P1 always.
2. **M-49 versus §8.3**: the question `text` input is the `\answer` prompt; the preceding `display_element` carries the
   statement text split at `\embed`. A question without `\embed` follows the statement (info detail).
3. **Dynamic correct index on radio/checkbox** (`\answer{..}{\k;list}` with a computed index): the complement logic is not
   specified; handled as a gap.
4. **Question inside a control block** (conditional existence of a question): not specified; gap (never guessed).
5. **`fraction` question type**: used when the expected value is `a/b` with provably-integer operands (otherwise
    `integer`/`decimal`); the spec lists the three types but not the selection rule.
6. **`\integer` typing** is not carried by the target platform: values that are not provably integer are wrapped in
    `math_round ROUND` (WIMS `rint`), reported as an approximation where relevant.
7. **`mapping.json`/`templates.json` instead of YAML** (§11): the templates are `src/oef2xml/data/templates.json`; no
    YAML dependency. `--def`, `--mdef`, `--assets-dir`, `--schematron` are accepted; the `.sch` run and `<settings>`
    contents beyond REQ-OUT-6 are untested (Q1/Q9).
8. **Python version**: the development box has Python 3.13.5; `requires-python >= 3.12` as per §11.1. Not tested on 3.12.
9. **Report `fidelite` at file level** (REQ-REP-7 as worded in v0.2.6): `approchee` when at least one question has
    `risque_evaluation` or the file has no question block, else `non_verifiee`. The spec gives the per-question rule
    precisely and the file rule by implication; implemented as stated.
10. **RT-A from the Linux `xml2oef` build**: the gate used `/workspace/xml2oef/bin/xml2oef-linux-amd64` and the Linux
    `oef2wims` of `/workspace/oefc/wims-runtime`; the E2 Windows wrappers were not exercised here.
