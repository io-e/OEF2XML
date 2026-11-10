# P1 open questions

Rule (owner): an item is listed here only if the spec is silent or contradicts itself on a case, or if an acceptance
criterion cannot be met without changing a requirement. Everything else became a G-nn gap (placeholder + taint,
file `partiel`) and the work went on. Numbers come from `reports/mvp_gate.md` (full corpus, 1433 files).

## A. Acceptance criteria that cannot be met as written

1. **§14.2 Gn threshold (≥ 260 of 324 M1 files with Q ≥ 1) is unreachable.** Measured 219 of 324. Only 223 of the 324
   files contain at least one `\answer`/`\choice` (101 are figure-only, no question directive at all), so no tool can
   exceed 223 < 260. The gate prints this bound next to the number. Needs: lower the threshold (≤ 223) or redefine M1.
   H (4 of 5 ≥ 4), Gn echec 0 % (≤ 1 %), 0 crash and 212/212 M files accounted for are met.
2. **AC-8 / §13.3 "0 DIFF-SILENT in RT-A" versus the phase plan.** The OEF files of Gn were produced by the forward
   converter: they contain `\x2oN` temporaries, `x2o_q` wrappers, `_v` renames, `\real`/`\integer` typing, post-statement
   definitions and `\embed` placement that the reverse tool keeps as ordinary OEF in P1 (idiom recognition is REQ-IDIOM-2,
   phase P2). The round trip therefore never reproduces the source structure. To keep the verdict honest, each such
   structural change is reported as an `approximation` detail at the source line (`idiom:x2o-temporary` REQ-IDIOM-2,
   `def:type-of-copy`, `def:name-trailing-underscore`, `title:length`, `list-item-whitespace`, `embed`, …) and the
   comparator treats a difference as DIFF-EXPLAINED only when such a detail (or a gap, or the REQ-OUT-4 post-definition
   info) covers the lines. Result: IDENTICAL 2, DIFF-EXPLAINED 1095, **DIFF-SILENT 3 of 1100** (01019, 01049, 01077: after a
   gap on `evalue()` the forward converter drops four `\real{i=0}` initialisations that no emitted block reads; the
   converter emits them and reports nothing for them). Needs: confirm that "approximation detail on every
   idiom-induced difference" is acceptable for P1, or move the 0-DIFF-SILENT rule to P2.
3. **RT-A comparison normalisations beyond N1–N8** (documented in `tools/roundtrip.py`): N3 extension (`_v` suffix added
   by the forward converter to names starting with `x2o` or ending in `_v`), N5b (expression AST canonicalisation),
   N9 (`\integer` = `rint`), N10 (`\if{num=num}` ≡ `\ifval`), N11 (`\integer`/`\real` equivalence when the value is
   provably integer). Spec §13.3 lists N1–N8 only. Needs: approval or rejection of these extensions.

## B. Spec silent or self-contradictory

4. **`non_traduits` defined twice** (REQ-REP-2: map of constructs; REQ-REP-4: counter). Implemented as the counter
   `directives_non_traduites` plus the map `non_traduits`.
5. **G-22 in P1.** AC-8 forbids `complet` for a file with a G-22 marker, but G-22 handling is listed in P2 with idioms,
   and `--idioms off` does not switch G-22 off (REQ-IDIOM-1 is unconditional). G-22 is handled in P1 always.
6. **Missing gap ids** for: `\feedback`, `\complex`/`\parameter`/`\variable`/`\wims` directives, text-level control
   directives, definitions after `\statement`. Currently REQ-TODO-1 (feedback, deferred to P3), G-11 and REQ-OUT-4 (info,
   not emitted).
7. **M-49 versus §8.3**: the question `text` input is the `\answer` prompt; the preceding `display_element` carries the
   statement text split at `\embed`. A question without `\embed` follows the statement (info detail).
8. **Inverse trig under `--trig-units`**: the spec converts the argument of `sin/cos/tan`; `asin/acos/atan` results are
   not covered, so they stay a G-21 gap.
9. **Dynamic correct index on radio/checkbox** (`\answer{..}{\k;list}` with a computed index): the complement logic is not
   specified; handled as a gap.
10. **Question inside a control block** (conditional existence of a question): not specified; gap (never guessed).
11. **`fraction` question type**: used when the expected value is `a/b` with provably-integer operands (otherwise
    `integer`/`decimal`); the spec lists the three types but not the selection rule.
12. **`\integer` typing** is not carried by the target platform: values that are not provably integer are wrapped in
    `math_round ROUND` (WIMS `rint`), reported as an approximation where relevant.
13. **`mapping.json`/`templates.json` instead of YAML** (§11): the templates are `src/oef2xml/data/templates.json`; no
    YAML dependency. `--def`, `--mdef`, `--assets-dir`, `--schematron` are accepted; the `.sch` run and `<settings>`
    contents beyond REQ-OUT-6 are untested (Q1/Q9).
14. **Python version**: the development box has Python 3.13.5; `requires-python >= 3.12` as per §11.1. Not tested on 3.12.
