# OEF2XML — Owner decisions log

Decisions taken by the project owner (Arnaud Lefrancois). Each entry gives the decision, the date, and where it applies.
The specification (`docs/CAHIER_DES_CHARGES_OEF2XML.md`) is the authority for details; this file records *when* and *why* a choice was made.

| ID | Date | Decision | Applies to |
|---|---|---|---|
| D-01 | 2026-11-09 | Implementation language is **Python 3.12** with `lxml` (owner's language, same as `oef_validate.py`, `oef2html.py`). A standalone Windows exe (PyInstaller) is **optional, phase P4** (Q11). | §11.1, §15 |
| D-02 | 2026-11-09 | Licence **AGPL-3.0** (compatible with WIMS GPL-2.0-or-later and LaRuche GPL-3.0). | `LICENSE` |
| D-03 | 2026-11-09 | Repository is **public**. | GitHub |
| D-04 | 2026-11-09 | "ELEDA" is replaced by **"XML program"** in documents and file names (`XML_program_v1.*`, `XML_program_v2.*`). | whole repo |
| D-05 | 2026-11-09 | The XML **namespace `urn:eleda:program:v1` and root element `<eleda-program>` stay unchanged** (renaming would break existing files; names starting with "xml" are reserved in XML). | REQ-OUT-*, schemas |
| D-06 | 2026-11-09 | Terminology: **"XML program"** = the file format; **"target platform"** = the platform that imports, runs and grades it. | §1 |
| D-07 | 2026-11-09 | `--trig-units deg\|rad` has **no default**; without it every trig call is gap G-21. | REQ-EXPR-4 |
| D-08 | 2026-11-09 | The `validation/` folder is **not modified** by the tool's development (REQ-ARCH-5). | `validation/` |
| D-09 | 2026-11-09 | Development rules: requirement ids (REQ/M-nn/G-nn) in code and reports from the first commit; deterministic output; **no network, no LLM**. | P0+ |
| D-10 | 2026-11-10 | **Never stop, never guess.** Anything that would require guessing exercise logic, or a block shape absent from `xml_block_catalog.json`, becomes a **gap** (G-nn placeholder + taint, file `partiel`; REQ-TODO-2/3, REQ-SCH-2/4). Ask the owner **only** if the spec is silent or contradictory, or an acceptance criterion cannot be met without changing a requirement. Such questions are recorded in `docs/P1_QUESTIONS.md`, which lives on branch `p0-p1` until PR #1 is merged. | P0+, `docs/P1_QUESTIONS.md` (branch `p0-p1`) |
| D-11 | 2026-11-10 | P1 code goes through a branch and **pull request** (`p0-p1`, PR #1); no direct code push to `main`. Documentation may be pushed to `main`. | workflow |
| D-12 | 2026-11-10 | The Codex v0.3 proposal is kept as a **reviewed amendment**, not a replacement; the §15 roadmap is kept and hardening items are added. Files in `docs/reviews/`. | spec v0.2.6 / v0.3 |
| D-13 | 2026-11-10 | **`<iframe>` is always a gap** (G-19 family), like `<script>`, `<form>`, `<input>`. The 12 Gn files with YouTube embeds become `partiel`. The default `--html pass` is kept for other HTML. | M-48, G-19, §12.1, R4 |
| D-14 | 2026-11-10 | Files that lose `\precision` or `weight=`: **flag only** (per-question `risque_evaluation`, with `fidelite: approchee` on those questions); `statut` is **not** demoted. | REQ-REP-2, REQ-REP-3, REQ-REP-7, REQ-REP-8, M-07, G-05 |
| D-15 | 2026-11-10 | **Gn MVP threshold = 80 % of the phase-1 Gn files (the 324 `M1` Gn files) whose source has `\answer` or `\choice`** (currently 223 of the 324, so ≥ 179), computed by the gate, not hard-coded (the earlier fixed count was unreachable). | §14.2 |
| D-16 | 2026-11-10 | **AC-8 "0 DIFF-SILENT" is required in P1** (not deferred to P2). Consequence: the **full RT-A run (1100 Gn files, already run by `tools/mvp_gate.py`)** is part of P1, and `xml2oef.exe` (the Go forward converter) is a P1 dependency. | AC-8, §13.3 RT-A (fixed sample `tests/data/rta_p1_sample.txt`), §15 |
| D-17 | 2026-11-10 | Trig mapping with `deg`: `sin/cos/tan` convert the **argument**; `asin/atan` convert the **result**; `acos` is a gap: `ACOS` is not observed in the 1116 catalogued programs (standard Blockly `math_trig` does define `ACOS`), so `acos` is a gap per D-10 / REQ-SCH-2; revisit under Q5. Recorded from the review; written into spec v0.2.6. | REQ-EXPR-4, G-21, B.2 |
| D-18 | 2026-11-10 | A `dropped-unread` info explains a round-trip difference only if (a) the block that read the definition is inside a reported gap (its gap id is recorded in the detail, field `cause_gap`), or (b) nothing in the source OEF reads the name either (`cause_gap: "unread-in-source"`). Any other `dropped-unread` counts as DIFF-SILENT. | §13.3, AC-8, B.2 |
| D-19 | 2026-11-10 | AC-11 is checked only on Windows 11. A Linux run of `tests/test_unicode_paths.py` is reported as `linux-only`, not `pass`. P1 can merge with AC-11 = `pending-windows`; it must pass before P2 ends. | AC-11, §14.2 |
| D-20 | 2026-11-10 | `\integer{x=e}` compiles to `rint(e)` (process.c:406): C rint, ties to even. When `e` is not provably an integer, it is wrapped in `math_round ROUND` and ALWAYS reported as `approximation` (construct `integer-rounding`), because the target platform's rounding of .5 is unverified (JavaScript `Math.round` rounds ties up: rint(2.5)=2, Math.round(2.5)=3). Revisit under Q5. | M-12, REQ-REP-2 |
| D-21 | 2026-11-10 | Mapping and templates are JSON (`src/oef2xml/data/*.json`); no YAML dependency. An option that is accepted but not implemented (currently `--def`, `--mdef`, `--assets-dir`, `--schematron`) prints `WARNING: <option> not implemented (REQ-…)` on stderr and adds `"options_non_implementees": [...]` to the batch report. It never changes the exit code. | §11, REQ-ARCH-2, REQ-REP-2 |
| D-22 | 2026-11-10 | File `fidelite` = the weakest fidelity of its question blocks, ordered `exacte` > `non_verifiee` > `approchee`. A file with no question block gets `fidelite: null` and the flag `sans_question`. It is not counted as `approchee`. | REQ-REP-7 |
| D-23 | 2026-11-10 | Current behaviour confirmed (P1 open question 1): G-22 runs even with `--idioms off`: keep; loss reporting is not optional, `--idioms` only toggles recognition of forward-converter patterns. | REQ-IDIOM-1, REQ-IDIOM-3, G-22 |
| D-24 | 2026-11-10 | Current behaviour confirmed (P1 open question 2): a question with no `\embed` goes after the statement: keep (that is where WIMS shows answer fields). | §8.3, M-49 |
| D-25 | 2026-11-10 | Current behaviour confirmed (P1 open question 3): a computed radio/checkbox index is a gap: keep (D-10). | §8.2, REQ-SCH-2 |
| D-26 | 2026-11-10 | Current behaviour confirmed (P1 open question 4): a question inside a control block is a gap: keep (D-10). | §8.3, REQ-SCH-2 |
| D-27 | 2026-11-10 | Current behaviour confirmed (P1 open question 5): `fraction` is chosen when the operands are provably integers: keep; added to §8.2 as a stricter reading of the 'written a/b' rule. | §8.2 |
| D-28 | 2026-11-10 | Current behaviour confirmed (P1 open question 8): Python 3.12 is closed; the owner ran the suite on 3.12 (58 pass, 2 skipped). | §11.1 |
| D-29 | 2026-11-10 | Current behaviour confirmed (P1 open question 10): Linux binaries (`oef2wims`, `xml2oef`) are acceptable for all acceptance criteria except AC-11 (see D-19). | AC-11, §14.2, REQ-ARCH-4 |

New decisions are appended with the next free D-nn id.
