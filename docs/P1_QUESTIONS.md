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

## Resolved by the owner review of PR #1 (spec v0.2.7, `docs/DECISIONS.md`)

| # | Question | Decision | Spec |
|---|---|---|---|
| 1 | G-22 runs even with `--idioms off` | **D-23** keep: loss reporting is not optional; `--idioms` only toggles recognition of forward-converter patterns | REQ-IDIOM-1, REQ-IDIOM-3, G-22 |
| 2 | Question without `\embed` goes after the statement | **D-24** keep (where WIMS shows answer fields) | §8.3, M-49 |
| 3 | Computed radio/checkbox index is a gap | **D-25** keep (D-10) | §8.2, REQ-SCH-2 |
| 4 | Question inside a control block is a gap | **D-26** keep (D-10) | §8.3, REQ-SCH-2 |
| 5 | `fraction` when the operands are provably integers | **D-27** keep; written into §8.2 as a stricter reading of "written a/b" | §8.2 |
| 6 | `\integer` values not provably integer wrapped in `math_round` | **D-20** keep, but ALWAYS an `approximation` `integer-rounding` (rint ties to even vs Math.round) | M-12, REQ-REP-2 |
| 7 | JSON instead of YAML; options accepted but unused | **D-21** JSON data (`mapping.json`); unimplemented option -> `WARNING: <option> not implemented (REQ-...)` + `options_non_implementees` | §11, REQ-ARCH-2, REQ-REP-2 |
| 8 | Python 3.12 not tested | **D-28** closed: owner ran 58 pass / 2 skipped on 3.12 | §11.1 |
| 9 | File-level `fidelite` implied rule | **D-22** weakest over the question blocks; no question block -> `null` + `sans_question` | REQ-REP-7 |
| 10 | Gate ran Linux builds only | **D-29** acceptable for all criteria except AC-11 (**D-19**: `pending-windows`) | AC-11, §14.2, REQ-ARCH-4 |

Also from the review: **D-18** (a `dropped-unread` explains a round-trip difference only with `cause_gap`) and **D-19**
(AC-11 `pending-windows` outside Windows 11).

## Still open

None. (AC-11 stays `pending-windows` until a Windows 11 run; it must pass before P2 ends, D-19.)
