# OEF2XML

Converts WIMS OEF exercise files (`.oef`) into **XML program** files (namespace `urn:eleda:program:v1`, root
`<eleda-program>`). The specification is `docs/CAHIER_DES_CHARGES_OEF2XML.md` (v0.2.5); every rule in the code and in
the reports carries the id of the requirement (`REQ-…`), mapping row (`M-nn`) or gap (`G-nn`) it implements.

Status: phases **P0** (skeleton, decoder, parser) and **P1** (semantic pass, emitter, validation, report, CLI) of the
spec. Feedback (`\feedback`), idiom recognition (`\x2o…` temporaries), images and the other phase-2/3 items are
reported as gaps or approximations, never guessed.

## Install and run

```
pip install -e .            # needs Python >= 3.12 and lxml (the development box runs Python 3.13.5)
oef2xml exercise.oef -o out/            # one file
oef2xml folder/ -r -o out/ --report out/report.json --csv out/report.tsv
python -m oef2xml --help
```

Main options (section 12 of the spec): `-o/--out`, `-r`, `--report FILE.json`, `--csv FILE.tsv`, `--encoding`,
`--gate auto|oef2wims|validator|none`, `--oef2wims PATH` (or `$OEF2XML_OEF2WIMS`), `--validate rng,xsd`,
`--strict` (partiel becomes echec), `--trig-units deg|rad` (the only way `sin/cos/tan` arguments are converted, G-21),
`--jobs N`, `--dump` / `--dump-ir` (pseudo-code / IR of one file), `--force`, `--suffix`.

Exit codes: `0` all files `complet`; `1` at least one `partiel`; `2` at least one `echec`; `64` bad usage.
`--out` must not be an input folder unless `--force` is given (REQ-BATCH-2). The output is deterministic: same input
and options give byte-identical XML, JSON and TSV.

### Statuses

* `complet`: no placeholder and at least one question block.
* `partiel`: at least one placeholder (a gap, REQ-TODO-*), or no question block (flag `aucune_question`).
* `echec`: the file cannot be decoded or parsed, or the compile gate refuses it (no XML is written).

Fidelity is `non_verifiee` when a question block was emitted, `approchee` otherwise; `exacte` is never reported while
open question Q5 (grading equivalence with WIMS) is open.

## Rule for gaps and open questions (owner decision)

* **Never stop and never guess.** If a rule would require guessing exercise logic, or a block shape is missing from
  `tools/corpus_stats/xml_block_catalog.json`, the construct becomes a **G-nn gap**: a placeholder block carrying the
  verbatim OEF fragment is written, everything that depends on it is tainted (REQ-TODO-2/3), and the file is `partiel`
  (REQ-SCH-2/4). The conversion goes on.
* An item is added to `docs/P1_QUESTIONS.md` **only** if the spec is silent or contradicts itself on a case, or if an
  acceptance criterion cannot be met without changing a requirement.
* `validation/` (schemas, fixtures, OEF validator) is read-only (REQ-ARCH-5). No network, no LLM call.

## Layout

```
src/oef2xml/   decode, parser (validator port), expr, textparse, blocks, shape (catalog shapes), convert (semantic
               pass, gaps, taint), emit (lxml), validate (RNG/XSD, shape lint, placeholder lint), gate (oef2wims on an
               ASCII scratch copy), pipeline, report, cli; data/ (templates.json, xml_block_catalog.json)
tests/         pytest suite (unit, schema fixtures, CLI exit codes, Unicode and 285-character paths, determinism)
tools/         corpus_stats/ (corpus statistics), mvp_gate.py (section 14.2 gate), roundtrip.py (RT-A comparator)
reports/       mvp_gate.md / mvp_gate.json written by tools/mvp_gate.py
validation/    read-only: XML program schemas v1 and fixtures, OEF validator
```

## Tests and the MVP gate

```
pytest -q                                   # set OEF2XML_OEF2WIMS=/path/to/oef2wims to also exercise the compile gate
python3 tools/mvp_gate.py --oef2wims PATH --xml2oef PATH --out reports      # section 14.2 numbers + AC checks + full RT-A (D-16)
OEF2XML_XML2OEF=PATH OEF2XML_CORPUS=DIR pytest tests/test_rta_sample.py   # fixed 100-file RT-A sample, tests/data/rta_p1_sample.txt
```

`tools/mvp_gate.py` converts the 1433 corpus files twice (AC-6), runs every acceptance check it can automate and the
RT-A round trip (OEF → XML → OEF with the reference forward converter, then comparison with the normalisations N1–N11
documented in `tools/roundtrip.py`). It writes `reports/mvp_gate.md` and `reports/mvp_gate.json`; its exit code is 0
only if the MVP passes as written. See `docs/P1_QUESTIONS.md` for the points where it cannot.

## Spec v0.2.6 behaviours worth knowing

* Gn MVP threshold is computed by the gate (80 % of the M1 files with `\answer`/`\choice`), never hard-coded (D-15).
* Active/external HTML (`<iframe>`, `<script>`, `on*=` ...) is always a G-19 gap, in every `--html` mode (D-13).
* `--gate-timeout SECONDS` (default 60); the report separates `gate`, `compilateur` (real oef2wims only) and `validateur`.
* Output names are collision-safe (casefold, `_2`, `_3`), written atomically; a stale XML next to an `echec` entry is removed
  and reported (`sortie_obsolete_supprimee`).
* Per-question `risque_evaluation` (lost `\precision`, `weight=`, ...) with `fidelite: approchee`; `statut` is not demoted (D-14).
* Fragments over 4000 characters become multi-part placeholders (`part k/N`), linted by SHA-256 of the reassembled text.
* `dropped-unread` info: a definition that no emitted block reads is reported, because the forward converter drops it (D-16).
