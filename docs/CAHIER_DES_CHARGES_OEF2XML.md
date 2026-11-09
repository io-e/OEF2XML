# OEF2XML — Requirements specification (cahier des charges)

| | |
|---|---|
| **Project** | OEF2XML — migrate WIMS OEF exercises to XML program (`urn:eleda:program:v1`) |
| **Repository** | https://github.com/io-e/OEF2XML — **public**, licence **AGPL-3.0** (`LICENSE`, §1.3, Q7) |
| **Owner** | Arnaud Lefrancois |
| **Version / date** | **v0.2.5 — 2026-11-10** (supersedes v0.2 draft and v0.1, which was truncated after §12) |
| **Language** | English (French section titles kept only where they name existing artefacts) |
| **Status** | For review. Nothing in this document has been implemented. Published in the repository under `docs/`. |
| **Verified against** | WIMS **4.31b** `oef2wims` sources (the only WIMS version available on the box), XML schema **v1** (RNG `CLAUDE_V1_1`, XSD), 1116 real XML programs, 1438 OEF files (Appendix C). XML schema v2 and Schematron were **not** supplied (Q1). |

Keywords MUST / SHOULD / MAY follow RFC 2119. Requirement identifiers (`REQ-…`) are stable so tests and the conversion report can cite them.

### Changelog v0.2.4 → v0.2.5
- §1 now defines two terms: **XML program** (the file format, namespace `urn:eleda:program:v1`, root `<eleda-program>`) and **target platform** (the platform that imports, runs and grades it). The v0.2.4 rename had replaced both with "XML"; every platform statement now says "target platform".
- Appendix B.2: the `rad` case of the forward trig idiom is stated.

### Changelog v0.2.3 → v0.2.4
- Renamed throughout: the format is called **XML program**; schema files `XML_program_v1.*` / `XML_program_v2.*`, checker `XML_program_v2_Test-ProgramsXml-AllSchemas.ps1`, block catalogue `xml_block_catalog.*`; owner paths replaced by `<project>`. The namespace and root element are unchanged.

### Changelog v0.2.2 → v0.2.3
- Q7 closed: AGPL-3.0 (`LICENSE` added; compatible with WIMS GPL v2+ and LaRuche GPL-3.0). The owner's v2 schema checker `XML_program_v2_Test-ProgramsXml-AllSchemas.ps1` is committed in `validation/xml/` (the v2 schemas it needs are still to be supplied, Q1).

### Changelog v0.2.1 → v0.2.2
- §11.1 closed: Python 3.12 (Go has no native RNG/XSD validation; shared logic lives in data files; round-trip calls `xml2oef.exe` as a process). Q11 closed: PyInstaller exe optional in P4.

### Changelog v0.2 → v0.2.1
- REQ-EXPR-4: `--trig-units deg|rad` was inverted. It now names the unit the target platform expects: `rad` keeps the argument, `deg` wraps it as `x × 180/π`; the forward idiom `sin(x*pi/180)` is handled separately (Appendix B.2).
- REQ-VAL-4: the fixtures are committed. REQ-TODO-1: the catalogue covers 1116 programs.
- Reproducibility of §14.2: `tools/corpus_stats/data/corpus.map` and `per_file.csv` are committed (the OEF corpus itself is not: upstream files are WIMS GPL material and the generated files come from the owner's private programs).
- §14: note that the phase-1 gate on hand-written files rests on 5 files only and says little about real OEF until the E-O set (Q2) exists.

### Changelog v0.1 → v0.2

v0.1 stopped in the middle of §12 (517 lines) and referred to §13, §17 and Appendices A/B that did not exist. v0.2 completes the document and applies an external review (12 points, listed with their resolution in the author's report). Summary:

- **Completed**: §13 (validation and round trips), §14 (acceptance criteria), §15 (phases), §16 (risks), §17 (open questions Q1–Q13 **and** schema change requests SC-1…SC-5, see §17.1/§17.2), Appendices A (corpus statistics, answer classes, WIMS command tables with source line numbers), B (XML block catalogue, reverse idioms), C (artefacts, reproduction, evidence index). All `§`, `Q`, `AC-`, `REQ-`, `G-`, `M-`, `R` and Appendix references resolve (checked by script, Appendix C.4).
- **Targets per corpus** (§14.2): explicit target / acceptable shares of `complet` / `partiel` / `echec` for the hand-written upstream set (H), all upstream (U) and the xml2oef-generated set (Gn), derived from the upper bounds of `scope_bounds.py`.
- **Safety**: trigonometry is now a gap (G-21) unless `--trig-units` is given, with no default (REQ-EXPR-4); placeholders and fail-closed rule are conditional on the Schematron R05 being supplied (REQ-OUT-5, REQ-TODO-4, Q1).
- **Schema facts**: `<description/>` is always emitted (REQ-LANG-1); comment-icon format checked on 2085 real icons and the placeholder carrier changed to `display_element` (REQ-TODO-1); repository state updated (§1.3).
- **WIMS facts re-checked**: size limits (REQ-IN-5), `\choice` has no `type=`, `--json` of the compiler wrapper (REQ-ARCH-4), reserved names (§7.1), prompt-length behaviour (§8.1).
- **Reporting**: `complet` is separated from "exact" (REQ-REP-3, REQ-REP-7, §8.2); the count invariant is redefined to survive step linearisation (REQ-REP-4).
- **Validation**: round-trip metric (normalisation N1–N8, thresholds) and a hand-written evaluation set (§13.3, Q2).
- The external review mentioned WIMS 4.27b; only 4.31b sources exist on the box, so nothing here is verified against 4.27b (Q3).

---

## 1. Context and goal

**Terminology (binding for the whole document).** **XML program** means the file format: an XML document in namespace `urn:eleda:program:v1` with root element `<eleda-program>`, described by the `XML_program_v1/v2` schemas. **Target platform** means the learning platform that imports, edits, runs and grades XML programs (its editor, Blockly loader, runtime and evaluation semantics). "XML block" or "XML schema" always refers to the format; any statement about behaviour (units, rendering, grading, import) refers to the target platform. The namespace and root element MUST NOT be renamed.

### 1.1 Existing pipeline (forward direction)

The owner already runs a one-way pipeline from the target platform to WIMS (facts from the 2026-10-28 handoff "JSON2OEF R7 CODEX v1" and from the `xml2oef` sources found on the box):

```
target-platform JSON ──► XML program (urn:eleda:program:v1) ──► OEF ──► oef2wims (.def) ──► wims.cgi
   1116 programs     1116/1116 converted            Go and JS xml2oef:           1100/1100 compile
                     DTD/XSD/RNG 1116 pass          466 complete / 634 partial   (oef2wims-log.exe,
                     Schematron 1111 pass, 5 fail   / 16 failed (MAX_DEFINE)     oef2wims-v2.exe)
```

- Schemas: `XML_program_v2.{dtd,xsd,rng,sch}` in `D:\ALF_Scripts\00-Schemas\03-xml_IR`.
- The XML→OEF converters (Go `xml2oef.exe`, JavaScript) *symbolically execute* the Blockly program: procedures are unrolled, sub-expressions become temporaries (`\x2oN`), questions become `\answer`/`\feedback`/`\condition`. The conversion is **lossy by design** and is documented in `xml2oef/MAPPING.md`.
- The pipeline's safety stance (handoff): never invent exercise logic; unresolved content becomes a TODO; the "reduced16" files are *not usable exercises* and must never be published.

### 1.2 Goal of OEF2XML (reverse direction)

Build a tool that reads WIMS OEF exercise files and writes **XML program** that:

1. is valid against the XML schemas (RNG/XSD, and Schematron where applicable);
2. preserves the exercise's statement, randomisation, expected answers and answer types wherever the XML block set can express them;
3. never invents or silently drops exercise logic: every OEF construct is either converted (exactly or approximately, and then *reported*) or isolated as a TODO placeholder carrying the original text;
4. produces a per-file conversion report (complete / partial / failed) in JSON and CSV, mirroring the report of the existing pipeline;
5. can be checked end to end by a round-trip test through the existing converters and the WIMS compiler.

### 1.3 Repository state (checked 2026-11-09 with `gh`)

`io-e/OEF2XML` is now **public** (default branch `main`, three commits: initial commit; this specification v0.1; the validation material). Content:

- `README.md` (9 bytes) and `docs/CAHIER_DES_CHARGES_OEF2XML.md` (v0.1, to be replaced by this v0.2);
- `validation/README.md`;
- `validation/oef/oef_validate/` — the Python OEF validator (`oef_validate.py`, `oef_spec.json`, `gen_spec.py`, `fuzz_oracle.py`, `compare_oracle.sh`, tests and the result files `resultats_wims-4.31b.txt`, `resultats_WIMS-modules.txt`, `resultats_LaRuche.txt`);
- `validation/oef/oef2wims/` — the E2 compiler wrappers: C sources (`sources/v2/oef2wims_v2.c`, `sources/wrapper/oef2wims_log.c`, `sources/common/*.inc`), tests (`tests/*.ps1`, mock scripts), `LISEZMOI.txt`, `AMELIORATIONS.txt`, `SHA256SUMS_E2.txt` (no binaries are committed);
- `validation/xml/schemas_v1/XML_program_v1.{rng,xsd}` — the v1 schemas (the v2 schemas and the Schematron are **not** in the repository, Q1).

Licence: **AGPL-3.0** (`LICENSE`, decided 2026-11-10, Q7); there is no converter code yet. Compatibility: WIMS and its `oef2wims` are **GPL**, LaRuche is GPL-3.0 and the JavaScript `xml2oef` vendors it. Any OEF2XML code that is a port of, or copies tables from, the WIMS C sources is a derivative work; this specification therefore records *facts and identifiers* with source file/line references (Appendix A.3) and does not copy code. The existing `validation/` tree MUST be kept as is (REQ-ARCH-5); new code goes next to it.

---

## 2. Evidence base and caveats (read before trusting any number)

### 2.1 What was inspected

| Item | Where | Notes |
|---|---|---|
| Relax NG schema `CLAUDE_V1_1` | attachment `e744b791….xml` | **Version 1**, namespace `urn:eleda:program:v1`. Read in full. |
| XSD generated with Trang | attachment `b138e2db….xml` | Same grammar. The block-type enum becomes an XSD union with a catch-all `xs:pattern`. |
| Handoff JSON2OEF R7 CODEX v1 | attachment `44e04b8a….md` | Refers to **v2** schemas (`XML_program_v2.*`, RNG "extended for source_format=xml, `ar`, empty `langs`", Schematron rules incl. R05) **that were not available**. |
| WIMS 4.31b `oef2wims` C source | `/workspace/oefc/src431/src/OefMsg2wims/` (+ `Lib/liblines.c`) | Authoritative list of commands, answer types, special functions, limits; line references in Appendix A.3. **Only 4.31b was available** (an external review mentioned 4.27b: not verified, Q3). |
| XML program programs (ground truth) | `/workspace/xml_etudes` (1116 files) | Used to catalogue real block/field/input shapes (`xml_block_catalog.json`). |
| Existing converter | `/workspace/xml2oef` (Go + JS), `MAPPING.md`, `ANALYSE_XML.md`, `results/rapport.json` | Baseline for the inverse mapping (Appendix B.2) and for the report format. |
| OEF validator | `/workspace/oef-validator`, also in the repo under `validation/oef/oef_validate/` | Python; reported to agree with `oef2wims` on the upstream files (validator README). Reuse candidate. |
| Compiler wrappers | `/workspace/oefc/e2pkg/E2_build/sources/` (identical to the repo copy of `oef2wims_v2.c`) | Gate behaviour (REQ-ARCH-4). |
| OEF corpus | `/workspace/oefc/corpus` + `corpus.map` | See 2.2 — **not what the request assumed**. |

### 2.2 Corpus provenance — important correction

The request described the corpus as "1438 upstream WIMS 4.31b demo files". `corpus.map` shows otherwise:

| Origin | Files | What it is |
|---|---:|---|
| **Generated by the owner's own `xml2oef`** (`/workspace/oef_out/oef`) | **1100** | Output of the forward pipeline. Restricted, machine-written vocabulary (`\x2oN` temporaries, `\embed{replyN}`, `\ifval`, `\while`…). **Not evidence of how people write OEF.** Used here as the *round-trip / idiom set*. |
| Upstream WIMS 4.31b — class sources (`log/classes/*/src`) | 104 | Hand-written teacher exercises shipped with the tarball. **Best proxy for real OEF.** |
| Upstream — module data (`modules/…`) | 17 | Hand-written. |
| Upstream — **model templates** (`public_html/scripts/model/*/src`) | 212 | Templates of WIMS's OEF-generator tool: heavy use of template variables (`\format`, `\atype`, `\types[n]`, `\toef_var…`) — **not typical exercises**. 74 files have a *dynamic* answer type. |
| Own oef2wims test files `e1`–`e5` | 5 | Excluded from all statistics. |

So only **333** of 1438 files are upstream WIMS (104 + 212 + 17), and only **121** (104 + 17) are ordinary hand-written exercises. **Priorities in this spec rest on the upstream numbers, with the model templates called out separately; the 1100 generated files are used for regression and round-trip, never to justify what OEF "usually" contains.** None of these files is the owner's own hand-written OEF. See open question Q2.

Additional OEF material exists but was not analysed: `WIMS-modules_oef.zip` (129 files) and `LaRuche_oef.zip` (10 files) in `/workspace/oef-validator/corpus/`.

### 2.3 What the XML schema does and does not enforce

Read in full (RNG `CLAUDE_V1_1` and its Trang-generated XSD, both v1). Line numbers are those of the supplied files; they were re-checked for v0.2.

1. **The block-type enum is not a restriction.** `block-type-enum` lists 190 values and then ends with a *catch-all* `[a-zA-Z_][a-zA-Z0-9_]*` pattern (RNG line 440); the XSD has the same pattern inside the union (xs:pattern, line 1158). Any identifier validates.
2. **Fields, inputs, `extraState`, `settings`, icons are `any-content`.** The schema says nothing about which fields or inputs a block must have.
3. Consequently **"valid against RNG/XSD" does not mean "importable by the target platform" and does not mean "renders correctly"**. Schema validity is a necessary gate, not an acceptance criterion by itself.
4. `eleda-program/@source_format` is restricted to `json | yaml | ir | xml` (RNG lines 19–22). **There is no `oef` value**; emitting `source_format="oef"` fails RNG/XSD validation (SC-1).
5. `lang/@code` is restricted to `fr en es it de ar` (RNG lines 85–90). OEF also knows `ca`, `cn`, `nl`, `si` (`\title_ca` …) (SC-2).
6. **`lang-def` requires both `<title>` and `<description>`** (RNG lines 93–94): a `<lang>` element without `<description>` is invalid. Upstream OEF has no `\description` (0 of 333 files), so the converter must emit an **empty** `<description/>` (REQ-LANG-1).
7. Root children order is fixed: `name`, `author?`, `tags?`, `langs?`, `settings?`, `variables?`, `blocks` (`blocks/@languageVersion` required). `block@type` is required; `id`, `x`, `y` optional; children order: `extraState?`, `icons?`, `field*`, `input*`, `next?`. `shadow` carries only `field*`.
8. Block ids and variable ids in real files are random 20-character Blockly ids; `variables_get/set` refer to the `<variables>` table by `id`.
9. The v2 schemas (`XML_program_v2.{dtd,xsd,rng,sch}`) mentioned by the handoff, in particular Schematron rule **R05** ("a question block is required", handoff line 40), were **not supplied**; every statement about R05 in this document is conditional (Q1).

### 2.4 Mitigations (binding on the design)

- **REQ-SCH-1** The emitter MUST use a **hard internal whitelist**: only block types that appear in the schema's enum list (the 190 explicit values; the catch-all is never relied upon).
- **REQ-SCH-2** Field names, input names and `extraState` children MUST come from the observed catalogue `xml_block_catalog.json` (built from the 1116 real programs: 169 observed types, all inside the enum). A block type that has no entry in the catalogue MUST NOT be emitted.
- **REQ-SCH-3** The 21 enum values **never observed** in the 1116 programs MUST NOT be emitted, because no real field/input shape is known: `QUESTION`, `adjectives`, `arrow`, `conjugations`, `decimal`, `definis`, `denominator`, `determinants`, `dotted`, `integer`, `integerPositive`, `kids`, `letters`, `multiple`, `names`, `numerator`, `segment`, `string`, `table`, `unique`, `verbs`. (Several of these — `integer`, `decimal`, `string`, `unique`, `multiple`, `integerPositive` — are *values* of the `type` field of question blocks in real files, not block types.)
- **REQ-SCH-4** The tool MUST fail its own unit tests if any emitted block type, field name or input name is absent from the catalogue (a "shape lint", independent of RNG).
- **REQ-SCH-5** `source_format`: default `ir`, configurable by `--source-format {json,yaml,ir,xml}` until the schema owner adds an OEF value (SC-1, open question Q4). The tool MUST NOT emit a value outside the schema's list.
- **REQ-SCH-6** Importability MUST be tested against a real target-platform import/runtime if one can be provided (open question Q5); until then every acceptance statement says "schema-valid and shape-lint-clean", not "importable".
- **REQ-SCH-7** `<lang>` elements MUST always contain both `<title>` and `<description>` (possibly empty), see REQ-LANG-1.

---

## 3. Scope

### 3.1 In scope

- Reading OEF source files (variants in §4.1) and producing one XML program per OEF.
- A conversion report per file and per batch (§4.4), with statuses `complet`/`partiel`/`echec` (names kept identical to the existing report; see §4.4).
- Use of `oef2wims` as a syntax gate and, optionally, of the compiled `.def` as a cross-check (§4.2).
- Validation of outputs against RNG, XSD and — if supplied (Q1) — Schematron (§13.1), and a round-trip test harness with an evaluation set (§13.3).
- Command-line use on Windows 11 and Linux, batch mode, Unicode paths.
- Language metadata for `fr en es it de ar`.

### 3.2 Out of scope (explicitly)

- **Executing WIMS exercises** or reimplementing `wims.cgi`/the WIMS expression engine as an exercise runner. (The tool *parses* expressions; it does not evaluate them except for constant folding that is provably exact.)
- Generating exercise logic that is absent from the OEF (no invented distractors, solutions, feedback, hints).
- Re-creating WIMS-only interactive answer types that have no XML block (drag-and-drop, click-fill, puzzles, flashcards, crosswords, chemistry/Jmol editors, canvas drawing inputs): they are reported as **gaps** (§6.4), not emulated.
- Importing into the target platform, authentication, uploading.
- Converting other WIMS formats (`.def` as primary source, `.src` module files, `.phtml`, `.html` server pages) — the `.def` is only a *secondary* input (§4.2).
- Packaging asset files (images, audio) — the tool records references and can copy them (`--assets-dir`), but does not convert media.
- Editing or "improving" the OEF (LLM-based fixing is the separate `oef_llm_fix.py` tool).
- A graphical user interface (a later optional phase may add a minimal page, like `xml2oef/js/index.html`).
- Modifying the XML schemas (schema change requests SC-1…SC-5 are listed in §17.2).

---

## 4. Inputs and outputs

### 4.1 Primary input: OEF files

- **REQ-IN-1** Accept a list of files and/or directories (recursive on request) with extension `.oef` (case-insensitive).
- **REQ-IN-2** Accept the OEF dialect understood by WIMS 4.31b `oef2wims`: top-level directives `\name{…}` with 0–5 brace parameters (55 directives, Appendix A.3.1), brace/paren/bracket matching as in `find_matching` (`Lib/liblines.c:103`), directives inside `\if`/`\ifval`/`\for`/`\while` bodies scanned as top-level (the scan in `process()`, `oef2wims.c:171–230`), unknown `\name{…}` at top level skipped silently by `oef2wims` (`oef2wims.c:207–209`; the tool MUST warn instead).
- **REQ-IN-3** **Encoding detection** (`--encoding auto|utf-8|latin-1|cp1252`, default `auto`): BOM → UTF-8; else strict UTF-8; else ISO-8859-1/cp1252. In the upstream corpus **267 of 333 files (80%) are not valid UTF-8** (ISO-8859 text) and 66 are UTF-8; all 1100 generated files are UTF-8. The report MUST record the detected encoding. Output XML is always UTF-8.
- **REQ-IN-4** CRLF/LF/CR line endings and a trailing-whitespace-tolerant parser (4 upstream files use CRLF). `oef2wims` replaces CR and the bytes 0–6 by spaces (`getinp`, `oef2wims.c:143–165`); the parser MUST behave the same.
- **REQ-IN-5** **Size and limit handling, aligned with `oef2wims` and the validator** (Appendix A.3.4):
  - an **empty file** (0 bytes; `Empty source file.`, `oef2wims.c:430`) or a file of **≥ 199 999 bytes** (`MAX_FLEN`; `getinp` returns −1, `Source file bad or too long.`, `oef2wims.c:429`) is an **error → `echec`**, no XML written, message copied into the report;
  - **only** the 1024-directive cutoff is a **warning** (`LIMIT-1024`): `process()` stops scanning after `MAX_DEFINE`=1024 directives and silently ignores the rest (`oef2wims.c:171`), so the compiler gate is unreliable for the tail. The tool's own parser reads the whole file and converts it (the target platform has no such cap); `--strict-limits` turns the warning into `echec`. (No file of the corpus exceeds 1024 directives: upstream maximum 208, generated maximum 738.);
  - an unmatched `() [] {}` anywhere in the file is an error (`checkparentheses`, `oef2wims.c:431`) → `echec` (REQ-REP-3);
  - silent truncations in WIMS that are **reported as `info`**: `\title` longer than 80 bytes (`MAX_TITLEN`), `\choice` prompts (§8.1).
- **REQ-IN-6** **Includes / external definitions.** OEF has no `\include`. Two mechanisms act like one: the environment variable `oef2wims_mdef` (module-defined macro names, handled by `\mdef` and `$m_` substitution) and runtime file references (`\imagedir`, `\filedir`, `\confparm1..4`, `slib(...)` modules). The tool MUST: accept `--mdef NAME[,NAME…]`; treat any `\imagedir`/`\filedir` reference as an *asset reference* (§7.6); report every `slib(module/name …)` call as a dependency (upstream: `text/cutchoice2` 42, `draw/convpixel` 19, `oef/env` 12, `text/markgroup` 10 …). `imagedir` and `confparm1…4` are *predefined* text parameters of `oef2wims` (`oef2wims.c:437–442`) and are never defined in the file: references to them are not "undeclared variables".
- **REQ-IN-7** Template-variable OEF (the 212 model files: answer type given as `\var`, 74 files; dynamic `\language`, 3 files) MUST be detected (`ans:DYNAMIC`). A dynamic answer type cannot be mapped statically: that question is a gap (G-06, taint) and the file is **`partiel`** (never guessed; `echec` only under `--strict`). A model template that the compiler itself refuses (2 upstream files, AC-2) is `echec` through the gate.

### 4.2 Secondary input: compiled `.def` (optional)

`oef2wims` compiles `X.oef` into `X.def` (WIMS script). The `.def` is **lossy**: variable names become `$valN`, control flow becomes `!if/!goto`, answers become `replynameN/replygoodN/replytypeN`. Therefore:

- **REQ-DEF-1** The `.def` is never a source of exercise logic. It MAY be used only as: (a) proof that the OEF compiles (`--gate`); (b) a cross-check of counts (`replycnt`, `choicecnt`, `ansorder=r,c,…`, `conditioncnt`, `feedbackcnt`, `varcnt`) against what the parser found — a mismatch is a warning `DEF-MISMATCH`; (c) disambiguating answer-type aliases (e.g. `type=number` → `replytype=numeric`, `type=select` → `menu`) by reading `replytypeN`; (d) the answer/choice **order** in `ansorder`.
- **REQ-DEF-2** `--def FILE|DIR` supplies pre-compiled `.def` files (e.g. from `/workspace/oefc/pt/L`); without it, `--gate oef2wims` compiles on the fly.

### 4.3 Output: XML program

- **REQ-OUT-1** One `<stem>.xml` per OEF in the output directory (`--out`, default `./oef2xml_out`), UTF-8, XML declaration, root `<eleda-program xmlns="urn:eleda:program:v1" id="…" source_format="…">`, 2-space indentation like the existing files.
- **REQ-OUT-2** `@id` = file stem by default (`--id-from stem|hash`), `@source_format` per REQ-SCH-5, `<name>` = `\title` (fallback: file stem), `<author>` from `\author`.
- **REQ-OUT-3** **Deterministic**: two runs on identical input produce byte-identical XML. Block/variable ids are derived from `sha1(program id + structural path)` rendered in the Blockly id alphabet (20 chars), never from time or randomness.
- **REQ-OUT-4** The program body is one chain: `info` block → `<next>` chain of `variables_set`, `display_element`, `question_*`… (the structure of all 1115 real programs that have an `info` block). Placeholders (§6.5) are **orphan top-level blocks**, never part of that chain.
- **REQ-OUT-5** The output MUST validate against the XML **RNG and XSD** (v1 now, v2 when supplied). Validation against the **Schematron** is **conditional on Q1** (the v2 `.sch` was not supplied): when a `.sch` is given (`--schematron FILE`) it is run on every document; its rule R05 (question block required, as described by the handoff) is then applied as described in REQ-TODO-4; when none is given the report says `schematron: non_execute` and no acceptance criterion depends on it (§13.1, AC-4).
- **REQ-OUT-6** `<settings>`: emitted only with keys that are *known* (`maxAttempts` from `--max-attempts`, `hasNestedQuestion=false`). Timestamps (`createdAt`, `updatedAt`) and `template` are **omitted** unless `--stamp` is given (open question Q9). `<tags>`: from `\keywords`, plus the literal `TODO` domain tag when none is known (per the handoff, line 52, the v2 Schematron "treats an explicit `TODO` domain tag as acknowledged"; unverifiable without the `.sch`, Q1).
- **REQ-OUT-7** Variables: every variable referenced by a `variables_get/set` MUST appear in `<variables>`; OEF identifier names are kept verbatim (Unicode allowed, no x2o renaming).

### 4.4 Output: conversion report (JSON and CSV)

Mirror `xml2oef/results/rapport.json` and `validation.tsv` so the two directions can be compared with the same scripts.

- **REQ-REP-1** `--report FILE.json` — top level: `outil` (`oef2xml <version>`), `resume` `{complet, partiel, echec, fichiers}`, `fichiers[]`, `non_traduits_fichiers`, `non_traduits_occurrences`, `approximations_occurrences`.
- **REQ-REP-2** Each `fichiers[]` entry: `source`, `sortie`, `id`, `titre`, `statut` ∈ {`complet`,`partiel`,`echec`}, `fidelite` (REQ-REP-7), the question counters of REQ-REP-4 (`questions_source`, `questions_converties`, `questions_gap`, `questions_taint`, `blocs_question_emis`), `directives_source` and its dispositions (`directives_traduites`, `directives_approximees`, `directives_info`, `non_traduits`), `non_traduits` (construct → count), `approximations` (construct → count), `encodage`, `octets`, `details[]` with `niveau` (`info`|`approximation`|`non_traduit`|`erreur`), `ligne_oef`, `colonne_oef`, `construct` (e.g. `answer:clickfill`), `regle` (gap id from §6.4, e.g. `G-07`, or mapping id `M-nn`), `message`.
  Field names are kept in French where the existing report uses French, so existing tooling keeps working; `ligne_xml` becomes `ligne_oef`.
- **REQ-REP-3** Status definitions (same spirit as the existing pipeline). **`complet` means "nothing was lost or isolated", not "exactly equivalent"** (that is the separate `fidelite`, REQ-REP-7):
  - **complet** — every top-level directive and every executed construct was translated, with or without an approximation that is reported at level `approximation`; no placeholder, no taint-dropped question; compile gate OK; schema-valid.
  - **partiel** — at least one construct isolated as a placeholder (gap) *or* a question dropped because of taint (§6.5) *or* a dynamic-type question (REQ-IN-7); XML still written and schema-valid.
  - **echec** — no XML written: unreadable/undecodable file, empty file or size ≥ 199 999 bytes (REQ-IN-5), unmatched brackets, compile gate failed (the compiler's message and line/column are copied), or internal error. In `--strict` mode every `partiel` becomes `echec`.
- **REQ-REP-4** **No-silent-loss invariants** (redefined in v0.2 so that they hold when steps are linearised, REQ-STEP-1). The tool counts *source units*, never output blocks, and MUST assert both invariants, turning a violation into `echec` with an internal-error message:
  - **I1 (directives)** every top-level directive found by the parser receives exactly one disposition: `traduite` | `approximee` | `info` (recorded, no block) | `non_traduite` (gap placeholder or reported drop). `directives_source == directives_traduites + directives_approximees + directives_info + Σ non_traduits`.
  - **I2 (questions)** every `\answer`/`\choice` unit has exactly one disposition: converted, gap, or taint-dropped. `questions_source == questions_converties + questions_gap + questions_taint`. A converted question counts **once** even when linearised steps emit it several times.
  - **I3 (output blocks)** `blocs_question_emis == Σ copies(q)` over converted questions, where `copies(q)` = 1 except for questions duplicated by step linearisation (`copies(q)` = number of steps in which q is active, recorded in `details[]`). `blocs_question_emis` MUST also equal the number of `question_*` blocks counted by an **independent scan of the written XML** (so a mismatch detects an emitter bug).
- **REQ-REP-5** `--csv FILE.tsv` (tab-separated, like `validation.tsv`): `fichier, statut, fidelite, encodage, questions_source, questions_converties, blocs_question_emis, nb_gaps, nb_approx, compilateur, rng, xsd, schematron, message` (`schematron` = `ok`|`ko`|`non_execute`).
- **REQ-REP-6** Exit codes (as `xml2oef`): `0` all complete, `1` at least one partial, `2` at least one failed, `64` bad usage.
- **REQ-REP-7** **Fidelity is reported separately from completeness.** Each file and each converted construct carries `fidelite` ∈ {`exacte`, `approchee`, `non_verifiee`}. A construct is `exacte` only if (a) the mapping row is class E in §6 **and** (b) the target platform semantics it relies on are verified (§8.5; Q5). Until Q5 is answered, **every question block is at best `non_verifiee`** (structure is known from 1116 real programs, grading semantics are not), so a `complet` file can still be `non_verifiee`. The batch summary reports the three counts. No acceptance criterion may call a file "exact" unless its `fidelite` is `exacte` (§14).

---

## 5. Target model: how real XML programs are built

Everything below is observed in the 1116 real programs (`xml_block_catalog.py` → `xml_block_catalog.json`; 169 distinct block types, 1116 files, `source_format`: json 1019 / xml 97; 4 programs have no question block, 750 have exactly one).

- An XML program is an **executable Blockly program**, not a declarative exercise: `info` (fields `default_title`, `default_lang`, `default_description`, `max_attempts`, `default_feedback`) → `next` chain of statements. The chain sets variables, displays content (`display_element` with `object` input), and asks questions (`question_*` blocks).
- **Values** are built from expression blocks: `math_number{NUM}`, `text{TEXT}`, `variables_get{VAR id}`, `math_arithmetic{OP: ADD MINUS MULTIPLY DIVIDE POWER; A,B}`, `math_single{OP: ABS ROOT NEG LOG10 LN EXP; NUM}`, `math_round{OP: ROUND ROUNDDOWN ROUNDUP; NUM}`, `math_modulo`, `math_trig{OP: SIN COS TAN ASIN ATAN}`, `math_constant{CONSTANT: PI}`, `random_number{type: integer|decimal; min,max}`, `math_random_int{FROM,TO}`, `logic_compare{OP: EQ NEQ LT LTE GT GTE; A,B}`, `logic_operation`, `logic_negate`, `logic_ternary{IF,THEN,ELSE}`, `logic_boolean{BOOL: TRUE|FALSE}`.
- **Lists/text**: `lists_create_with{extraState/itemCount; ADD0…ADDn}`, `list_short_get{LIST,INDEX}`, `lists_getIndex{MODE: GET|GET_REMOVE|REMOVE; WHERE: FROM_START|FIRST|LAST|RANDOM; VALUE,AT}`, `lists_sort{TYPE: NUMERIC; DIRECTION: 1|-1}`, `shuffle_list{LIST}`, `lists_indexOf`, `text_join{ADD0…}`, `text_replace{FROM,TO,TEXT}`, `text_changeCase{CASE}`, `text_length`, `text_charAt`, `split_number`, …
- **Control**: `controls_if{IF0,DO0,…,ELSE; extraState hasElse, elseIfCount}`, `controls_for{VAR; FROM,TO,BY,DO}`, `controls_forEach{VAR; LIST,DO}`, `controls_repeat_ext{TIMES,DO}`, `controls_whileUntil{MODE: WHILE|UNTIL; BOOL,DO}`, `procedures_defnoreturn/defreturn/callnoreturn/callreturn`.
- **Display**: `display_element{object}`, `richtext_create_with{extraState/itemsCount; ADD0…}` (mixed text/variables/latex), `latex{LaTeX}`, `latex_paragraph_create_with`, `markdown{markdown}`, `text_multiline`, `special_character{character: br|hr}`, `set_alignment{alignment: center|left|right; item}`, `set_colour{colour; item}`, `set_size{size; item}`, `image{url, image_width, image_height, figure_caption}`, `video{embed_code}`, `sound`.
- **Questions** (blocks / programs): `question_open` 1777/676 (field `type`: integer 991, decimal 473, string 136, expression 98, fraction 73, integerPositive 6), `question_multiple_choices` 403/274 (`type`: unique 374, multiple 29; inputs `solution` = list of right answers, `proposals` = list of wrong answers, `nb_proposals_to_display`), `question_true_false` 84/46 (`solution` is a boolean), `question_reorder` 23, `question_associate` 52 (`solution1`,`solution2`), `question_figure` 137 (click on a figure). Common fields: `moreOptions`, `mutation_shape` (`value`|`statement`), `answer`, `question` (variable ids of kind `QUESTION`), `default_feedbacks`, `raw_options` (a JSON string such as `{}`, `{"callbackSolution":true}`, `{"length":4}`); common inputs `text` (the prompt), `solution`, `feedbacks`; `extraState` children `displaymoreOptions`, `statement`.
- **Feedback**: input `feedbacks` of a question, `context_question`, `feedback_global`, `random_message`, `is_solution_found`, `current_attempt`, `max_attempts`.
- **Difficulty variants**: `versions` (344 programs; labels like "☆ / ☆☆ / ☆☆☆"). OEF has no equivalent concept.
- **Orphan top-level blocks** exist in real files (procedures, never-executed blocks), so placeholders as orphan blocks (§6.5) are consistent with real files. Of the 1116 programs, all but 1 have an `info` block at the head of the main chain (REQ-OUT-4).
- **Comment icons** (`<icons><comment …/></icons>`) occur **2085 times** in 1071 of the 1116 programs, on exactly 10 block types: `info` 1050, `procedures_defnoreturn` 420, `variables_set` 374, `procedures_defreturn` 153, `draw_in_board` 35, `display_element` 17, `controls_whileUntil` 11, `controls_if` 9, `statement` 8, `question_true_false` 8. All 2085 carry the four attributes `text`, `pinned` (`True` 819 / `False` 1266), `height`, `width`, and no child. The exact format is quoted in REQ-TODO-1; **no real icon sits on a `text` block** (see REQ-TODO-1, Q5).

The **semantics of several question fields is not documented** in the material available (`mutation_shape`, `moreOptions`, `raw_options`, `answer`, `question`, `default_feedbacks`, `extraState/statement`). REQ-MAP-Q-TEMPLATE below therefore copies the *modal* shapes of real files and marks them provisional (open question Q5).

---

## 6. Mapping OEF → the target platform

Fidelity codes: **E** exact (semantics preserved; for anything that depends on the target platform's own evaluation semantics this requires them to be *verified*, REQ-REP-7, Q5), **A** approximate (converted, reported at level `approximation`), **G** gap (no equivalent: placeholder + report), **P** planned for a later phase (until then behaves as G). Only block types that exist in the schema enum *and* in the observed catalogue are used (REQ-SCH-1..3).

### 6.1 Header and metadata

| ID | OEF | The target platform | Fid. | Notes |
|---|---|---|---|---|
| M-01 | `\title{T}` | `<name>`, `<lang code=L><title>`, `info.default_title` | E | Title ≤ 80 bytes in WIMS; no limit in the target platform. |
| M-02 | `\language{L}` | `info.default_lang`, `<lang code=L>` | E for `fr en es it de ar` | `ca cn nl si`, dynamic `\language{\x}`: **G-04**. No `\language` (279/333 upstream files): use `--default-lang` (default `fr`), report `info`. |
| M-03 | `\title_xx{T}` | additional `<lang code=xx><title>` | E for the six codes | Not present in either corpus; supported for completeness. |
| M-04 | `\author{A}` | `<author>` | E | |
| M-05 | `\description{D}` | `<lang>/<description>`, `info.default_description` | E | Present in 595 generated files, 0 upstream. **No `\description` (all 333 upstream files): emit an empty `<description/>`** — the schema requires the element (REQ-LANG-1; fixture `valid/minimal_info_chain.xml`, §13.1). |
| M-06 | `\keywords{…}` | `<tags><tag>` | A | + literal `TODO` domain tag when no domain is known (REQ-OUT-6). |
| M-07 | `\email`, `\credits`, `\css`, `\observation`, `\format`, `\computeanswer`, `\precision`, `\range` | none | **G-02** | Recorded as `info` details; copied verbatim into a comment icon on the `info` block (not shown to students). `\precision` (66 upstream files) and `\range` (43) influence numeric comparison and plotting in WIMS; their loss is reported at level `approximation` on every `numeric` answer of the file. |
| M-08 | (no OEF equivalent) `max_attempts`, `default_feedback` | `info.max_attempts`, `info.default_feedback` | A | Value from `--max-attempts` (default 1 — open question Q8) and `false`; always reported (`info`), never presented as coming from the OEF. |

### 6.2 Variables, expressions, control flow

The OEF expression language is described in §7. Mapping of definitions and control:

| ID | OEF | The target platform | Fid. | Notes |
|---|---|---|---|---|
| M-10 | `\integer{a=randint(m..n)}` | `variables_set{VAR=a}` ← `random_number{type=integer; min,max}` | E | Reverse of `xml2oef` rule. |
| M-11 | `\real{x=random(m..n)}` | `random_number{type=decimal}` | A | WIMS `random(m..n)` is a real in range; resolution differs. |
| M-12 | `\integer{…}`, `\real{…}`, `\rational{…}` with arithmetic | `math_arithmetic`, `math_single`, `math_round`, `math_modulo`, `math_constant`, `variables_get` | E (A for `\rational`) | `\rational` has no dedicated numeric type. The `fraction` *block* exists and is observed (555 blocks, 146 programs; inputs `dividend`, `divisor`), but a rational *value* is kept as `math_arithmetic DIVIDE` (A) unless the OEF value is a literal `a/b`, which MAY map to `fraction`. Reported either way. |
| M-13 | `\text{s=literal}` | `variables_set` ← `text` | E | HTML entities (`&#44;` etc.) are kept verbatim in the text. |
| M-14 | `\text{L=a,b,c}` used as a list | `lists_create_with{itemCount; ADDn}` | A | OEF lists are comma-separated strings; typing is *inferred from use* (`items`, `item`, `shuffle`, `randitem`, `\L[i]`, `\for{x in \L}`, `wims(… items …)`). Ambiguous → keep as `text` and report. |
| M-15 | `shuffle(L)` | `shuffle_list{LIST}` | E | |
| M-16 | `randitem(L)` / `randomitem(L)` / `pickone(…)` | `lists_getIndex{MODE=GET; WHERE=RANDOM}` | E | |
| M-17 | `item(i,L)`, `\L[i]` | `list_short_get{LIST,INDEX}` | E | 1-based on both sides. |
| M-18 | `items(L)` (count) | `lists_length{VALUE}` | E | Observed: 659 blocks, 103 programs. |
| M-19 | `position(x,L)` / `positionof` | `lists_indexOf{END=FIRST; VALUE,FIND}` | A | Only `END=FIRST` observed (363 blocks); which of `VALUE`/`FIND` is the list is to be confirmed on exemplars. |
| M-20 | `wims(sort numeric items L)` | `lists_sort{TYPE=NUMERIC; DIRECTION=1}` | E | |
| M-21 | `\matrix{M=a,b\c,d}`, `row/rows/column`, `\M[i;j]` | `matrix{typeOf=text or list; input}`, `table_matrix{type=table; LINE_n}`, `data_table{LINE_n}`, `matrix_short_get{MATRIX,I,J}` | P | The meaning of `typeOf` and the line/column layout of `LINE_n` need exemplars; upstream: 156 files use `\matrix` (47%). |
| M-22 | `\function{f=a*x^2+…}` | `variables_set` ← `text` (formula string) | A | The formula is kept as text; used by `evalue`/`diff`. The target platform has `expression`, `evaluate{expression,variable,value}`, `derivative{expression,variable}`. |
| M-23 | `evalue(f, x=v)` | `evaluate{expression,variable,value}` | E | |
| M-24 | `diff(f,x)` | `derivative{expression,variable}` | E | |
| M-25 | `simplify(f)` | `simplify_algebrite{expression}` | A | Different CAS (WIMS/PARI vs Algebrite): results can differ in form. |
| M-26 | `maxima(expand(f))` | `expand_algebrite{expression}` | A | Same caveat. |
| M-27 | `pari(Pol([..]))`, `pari(Vec(..))`, `pari(poldegree(..))`, `pari(isprime(..))` | `polynom_with_coefficients`, `coefficients`, `degree`, `math_number_property{PROPERTY=PRIME}` | A | Only the patterns that `xml2oef` itself emits (Appendix B.2); any other `pari(…)` is **G-11**. |
| M-28 | `\if{c}{then}{else}`, `\ifval{c}{…}` | `controls_if{IF0,DO0,ELSE; extraState hasElse}` with `logic_compare` | E | Generated corpus: 531 `\if`, 738 `\ifval` files. |
| M-29 | `\for{i=a to b}{…}`, `\for{x in \L}{…}`, `\while{c}{…}` | `controls_for{VAR;FROM,TO,BY,DO}`, `controls_forEach`, `controls_whileUntil{MODE=WHILE}` | E | Upstream: 145 files `\for`, 126 `\if`, 5 `\while`. |
| M-30 | `==`, `!=`, `<`, `<=`, `>`, `>=`, `and`, `or`, `not` | `logic_compare{OP}`, `logic_operation`, `logic_negate` | E | `\ifval` numeric equality vs `\if` text equality: both → `EQ`; reported `A` when a text/number mix is detected. |

### 6.3 Statement, text, math markup, media

| ID | OEF | The target platform | Fid. | Notes |
|---|---|---|---|---|
| M-40 | `\statement{…}` | one or more `display_element{object}` | A | The OEF statement is **HTML + `\var` substitutions + `\embed{replyN}` markers + `\(…\)` LaTeX**. Target-platform content is assembled from blocks; there is no verified "raw HTML" block. |
| M-41 | plain text runs | `text{TEXT}` inside `richtext_create_with{itemsCount; ADDn}` | E | Newline in source → `special_character{character=br}` only when the source has `<br>`; raw newlines are preserved in `TEXT`. |
| M-42 | `\x`, `\x[i]` (variable references) | `variables_get{VAR id}` / `list_short_get` | E | Unresolved name → taint (§6.5). |
| M-43 | `\(…\)` / `\[…\]` LaTeX | `latex{LaTeX}`, `latex_paragraph_create_with` | E | Upstream: `\(` in 50 files; generated: 576 files. |
| M-44 | `<b>`, `<i>`, `<strong>`, `<em>` | `markdown{markdown}` (`**…**`, `*…*`) | A | Reverse of `xml2oef`. |
| M-45 | `<br>`, `<hr>` | `special_character{character=br or hr}` | E | |
| M-46 | `<div class="wimscenter">`, `<p class="wimscenter">`, `align=center` | `set_alignment{alignment=center; item}` | A | Upstream: `wimscenter` in 133 files. |
| M-47 | `<img src="…">`, `\imagedir/…` | `image{url,image_width,image_height,figure_caption}` | A | Asset handling §7.6. Upstream: `<img` in 27 files, `\imagedir` in 41. |
| M-48 | any other HTML (`<table>` 38 files, `<a>` 204, `<span style>`, `<script>`, `<form>`, entities) | `text{TEXT}` containing the markup **verbatim** | A (risk) | It is **unknown whether the target platform renders raw HTML in a `text` block** (Q5/R4). Reported per element class; `--html strict` turns such fragments into **G-17** placeholders instead. |
| M-49 | `\embed{reply1}` / `\embed{reply1,10}` / `\embed{choice1}` | split point: text before it becomes the prompt of that question block (§8.3) | A | `\embed` occurs in 281/333 upstream files (445 occurrences); all 1411 generated ones are `replyN`. |
| M-50 | `\reply1`, `\sc_reply1`, `\step`, `\choice1`, `\result` in text | no equivalent | **G-18** | Student-answer references appear in 32 upstream (`\reply`), 6 (`\sc_reply`), 47 (`\step`) files and in 323/392 generated files; usable only inside feedback conversion (§8.5). |
| M-51 | `\hint{…}`, `\help{…}`, `\solution{…}` | none verified | **G-03 / P** | `\solution` (10 upstream files) is a *worked solution shown after the answer*; the target platform's `solution` input is the *expected answer*, a different concept. A later phase may map it to a post-answer display inside `feedbacks`, after owner confirmation (Q10). |
| M-52 | `\latex{…}` (TeX version, 52 files), `\format{tex}` | none | **G-16** | |
| M-53 | `\plot{…}`, `draw(…)`, `canvasdraw(…)`, `drawtikz(…)`, flydraw scripts | `board_geometric`, `point`, `line`, `circle`, `polygon`, `draw_in_board`, `graph_of_function` | **G-09 / P** | Simple flydraw primitives (point, line, circle, plot of a function) MAY be mapped in phase 4; the forward converter itself leaves all geometry untranslated. `draw(…)`: 37 upstream files. |

### 6.4 Gap register (constructs with no XML equivalent)

Every gap has an id used in the report (`regle`) and in the placeholder comment. Frequencies: upstream = 333 WIMS files (class 104 / modules 17 / models 212); gen = 1100 generated files.

| Gap | OEF construct | Frequency | Handling |
|---|---|---|---|
| G-01 | `\email{}` | upstream 273 files | info + comment icon |
| G-02 | `\credits` 213, `\css` 49, `\observation`, `\format` 53, `\computeanswer` 57, `\precision` 66, `\range` 43 | upstream | info/approximation; verbatim comment |
| G-03 | `\hint` 19, `\help` 2, `\solution` 10 | upstream | placeholder (orphan text block with the original text) |
| G-04 | `\language` ∈ {ca,cn,nl,si} or dynamic | upstream: ca 1, dynamic 3 | map to `--default-lang`, report |
| G-05 | `option=` tokens other than the ones handled in §8.4; `weight=` (10 upstream occurrences) | upstream: `noanalyzeprint` 186 occ., `nonstop` 82, `detag` 40, `show` 25, `split` 21, `sort` 14 … | info + approximation on that question |
| G-06 | interactive/module answer types (§8.2): `clickfill`, `dragfill`, `mark`, `click`, `puzzle`, `flashcard`, `multipleclick`, `crossword`, `coord`, `jsxgraphcurve`, `chemdraw`, `jmolclick`, `vector`, `matrix`, `set`/`aset`/`fset`, `time`, `units`, `draw`, `code`, `compose`…, **and dynamic `type=\var`** (REQ-IN-7) | upstream: 209 of the 325 files that have an `\answer` contain at least one G answer (hand-written: 54 of 113); 74 files (hand-written 10) have a dynamic type | placeholder, taint |
| G-07 | `\special{…}` with first word `editarea`, `help`, `imagefill`, `imageinput`, `codeinput`, `drawinput` or `mathmlinput` | upstream: 58 files (editarea 49, help 19, imagefill 10, imageinput 3, codeinput 2, drawinput 1, mathmlinput 1) | placeholder |
| G-08 | dynamic `\steps`/`\nextstep` (conditional progression) | upstream: `\steps` 101 files, `\nextstep` 36 | placeholder (§9) |
| G-09 | drawing scripts (§6.3 M-53) | upstream `draw(` 37 files | placeholder |
| G-10 | `\matrix` shapes not yet mapped | upstream 156 files | placeholder until phase 2 |
| G-11 | `pari(…)`, `maxima(…)`, `yacas(…)`, `solve`, `int`, `det`, `mathexp_cut` beyond the reverse table | upstream `pari` 21 files, `maxima` 3; gen: `pari` 89 | placeholder + taint |
| G-12 | `wims(<subcommand>…)` outside the reverse table (§7.2) | upstream: **230 files, 2168 calls** (`replace` 274, `append` 269, `makelist` 232, `embraced` 216, `word` 158, `nonempty` 143, `items2words` 104 …) | placeholder + taint |
| G-13 | `slib(module/name …)` | upstream 102 files, 127 calls | placeholder + taint; dependency listed |
| G-14 | `\mdef` / `$m_` module macros | upstream: 0 files with `\mdef`; env `oef2wims_mdef` | placeholder |
| G-15 | `\condition`, `\conditions` (answer analysis) | upstream 24 + 14 files (251 `\condition` occurrences); gen 90 | phase 3 as `callbackSolution` style; before that placeholder + taint |
| G-16 | TeX output `\latex`, `\format{tex}` | upstream 52 files | info |
| G-17 | HTML that cannot be carried (only with `--html strict`) | — | placeholder |
| G-18 | `\replyN`, `\sc_replyN`, `\step`, `\choiceN`, `\result` outside feedback | see M-50 | placeholder / feedback phase |
| G-19 | `<script>`, `<form>`, `<input>` in statements | to be measured | placeholder |
| G-20 | languages with no XML lang (ca cn nl si) in `\title_xx` | — | dropped with report |
| G-21 | **trigonometric functions** `sin cos tan asin atan …` (units not confirmed, REQ-EXPR-4, Q6) | not measured per file | placeholder + taint, unless `--trig-units deg\|rad` is given explicitly |
| G-22 | `%% x2o NON TRADUIT …` marker lines left by the forward converter (REQ-IDIOM-1) | generated: 634 of 1100 files | recorded as gap (the XML block that was lost upstream stays lost) |

### 6.5 TODO / placeholder policy (never invent logic)

Aligned with the handoff's safety note: *unresolved content becomes a TODO; exercise logic is never invented.*

- **REQ-TODO-1 Placeholder form.** A gap is represented by a **top-level orphan block** (not reachable from `info`; never executed) of type `text` (in the enum; 49 204 `text` blocks in the 1116 catalogued programs, of which 187 are *top-level orphans* like a placeholder, none with an icon) with `x`,`y` outside the main chain's area, carrying a comment icon in **exactly the format of real files**:

  ```xml
  <block type="text" id="…" x="700" y="-266">
    <icons>
      <comment text="TODO[OEF2XML G-03] …" pinned="True" height="107" width="364" />
    </icons>
    <field name="TEXT"></field>
  </block>
  ```

  Evidence (real icons, `/workspace/xml_etudes/`): `1008.xml:40-42`, the `info` block of that program:
  ```xml
  <icons>
    <comment text="Modification possible : ordre de grandeur des diviseurs et dividendes affichés, … (Procédure &quot;Feedback&quot;)" pinned="True" height="107" width="364" />
  </icons>
  ```
  and `3368.xml:543-545` on a `display_element` block (full text, no elision):
  ```xml
  <icons>
    <comment text="N'oubliez pas d'afficher le graphique !" pinned="False" height="67" width="291" />
  </icons>
  ```
  `<icons>` is the first child after `extraState` (child order, §2.3 item 7); the icon is an attribute-only element in the XML namespace; `pinned` is the string `True`/`False`; `&` `<` `"` are XML-escaped. **Verified**: element and attributes (2085 occurrences, §5). **Not verified**: (a) that the target platform's Blockly loader displays a comment on a `text` block (no real icon is on a `text` block, even on the 187 orphan ones; carriers seen are listed in §5) and (b) newlines inside `text`. Both are open question Q5; until answered the carrier is switchable with `--placeholder-carrier text|display_element` (`display_element` has 17 real comment icons, 13 top-level instances exist). The comment text contains: the gap id, a one-line reason, the **source file, line and column**, and the **original OEF fragment copied verbatim** (length-capped at 4000 characters with a SHA-256 of the full fragment). The same TODO list is repeated on a comment icon of the `info` block (count + ids; real `info` blocks carry comment icons in 1050 programs). Schema-level proof that this shape validates: fixture `valid/minimal_info_chain.xml` (§13.1).
- **REQ-TODO-2** A placeholder MUST NOT contain a guessed expected answer, a guessed distractor, a guessed formula or a plausible-looking default value. Where the target needs a value that the OEF does not provide (e.g. `max_attempts`), the value comes from a visible CLI option and is reported as such.
- **REQ-TODO-3 Taint propagation.** A variable defined by a gap construct is *tainted*; any definition, statement fragment, question or feedback that **reads a tainted variable** is also not emitted (the construct becomes a gap with reason `depends on G-nn variable \x`) — **except** pure display of non-essential decoration, which is configurable and off by default (`--taint-display`). Consequence: the tool never emits a question whose solution depends on something it could not convert.
- **REQ-TODO-4 Fail closed (conditional on Q1).** A file whose questions are all gaps is written (so the TODOs are visible) and is `partiel`. **If** the v2 Schematron is supplied (Q1) and contains the rule that requires a question block (R05, per handoff line 40), such a file is *expected* to fail it — that is the intended signal, identical to the "reduced16" lesson of the handoff (a zero-question file is not an exercise and must not be deployed) — and the report records `schematron: ko (R05)`. **Without the `.sch`** the tool applies the same rule itself (no `question_*` block in the output ⇒ report flag `aucune_question`, never `complet`), so that the behaviour does not depend on a file that is not available. `--strict` makes it `echec`.
- **REQ-TODO-5** The report lists, per file, the gap ids and their counts; the batch summary lists the top gaps by affected files, so the owner can prioritise.
- **REQ-TODO-6** A lint (`--check-placeholders`) verifies for each partial file that every `TODO[` comment contains the verbatim fragment (hash check) and that no placeholder block is reachable from the `info` chain.

### 6.6 Idioms left by the forward converter (round-trip aware)

The 1100 generated OEF files are the output of `xml2oef`. Its conventions (Appendix B.2) are recognised by the reverse tool **only as explicit, enumerated patterns**:

- **REQ-IDIOM-1** A line `%% x2o NON TRADUIT [type, ligne XML n] : reason` (634 of 1100 generated files) records an XML block the forward converter could not translate. The reverse tool MUST turn each such line into a gap **G-22** (placeholder carrying the line verbatim): the file is then at best `partiel`. It MUST NOT claim `complet` for such a file, because the lost block cannot be recovered from the OEF. Lines `%% x2o approximation …` (659 files) become `approximation` details.
- **REQ-IDIOM-2** Temporaries `\x2oN`, `\x2orepN` (+ `\condition`), `\x2oversion` and the conventions of B.2 are interpreted only in the exact shapes listed there; any other use of these names is treated as ordinary OEF.
- **REQ-IDIOM-3** Idiom recognition is a mapping-table feature (`mapping.yaml`, REQ-ARCH-2), switchable (`--idioms on|off`, default on) so that hand-written OEF is never interpreted through forward-converter conventions by accident.

---

## 7. Variables, randomisation, expressions, CAS, markup, assets

### 7.1 Definitions and substitution

- OEF definition directives: `\integer \int \real \rational \complex \text \matrix \function \parameter \variable \mdef`. Corpus (upstream, definitions by occurrence): `\text` 6504, `\integer` 1365, `\matrix` 545, `\real` 205, `\function` 13, `\rational` 4. Hand-written subset (121 files): `\integer` in 66 files, `\text` 75, `\matrix` 39, `\real` 13.
- A directive has the form `\name{lhs = rhs}` or `\name{lhs}{rhs}`; `:=` is accepted by `oef2wims` (`checkeq` in `oef2wims.c`) and MUST be accepted.
- Reference syntax in later text and expressions: `\name`, `\name[i]` (list/char index), `\name[i;j]` (matrix cell). A reference to a name that was never defined is passed through by `oef2wims` (it becomes empty); the tool MUST report `undeclared variable` and treat the surrounding construct as tainted (§6.5). `oef2wims` itself substitutes the answer-time names `\reply`, `\result`, `\choice`, `\step`, `\sc_reply`, `\sc_choice` and `\reply_` (`repsubst`, `oeflines.c:111–138`) and predefines `imagedir`, `confparm1…4` (`oef2wims.c:437–442`): these MUST NOT become XML variables. (The forward converter additionally avoids the names `reply…`, `step`, `pi` when it *writes* OEF: that is its rule, `MAPPING.md:17`, not a WIMS rule.)
- **Evaluation order** matters in OEF: definitions before `\statement` are executed at exercise generation, definitions *after* `\statement` are executed after the answer (post-definitions, `postvarcnt`). The IR MUST keep this phase tag (`pre`/`post`) per definition because post-definitions only make sense inside feedback (§8.5).

### 7.2 Randomisation (semantics from `OefMsg2wims/sp.c`)

| OEF | Semantics | The target platform |
|---|---|---|
| `randint(a..b)` | integer in [a,b] | `random_number{type=integer}` (E) |
| `randint(a,b,c)` | pick one of the listed integers (comma form calls `randitem`) | `lists_getIndex{WHERE=RANDOM}` over `lists_create_with` (E) |
| `random(a..b)` | real in [a,b] (integer in an `\integer` context) | `random_number{type=decimal}` (A) |
| `random(a,b,c)` | pick one item | as `randint(a,b,c)` (E) |
| `pickone(…)` | same as `randint` | |
| `shuffle(L)` | random permutation of items | `shuffle_list` (E) |
| `randitem(L)`, `randomitem(L)` | random item | `lists_getIndex{WHERE=RANDOM}` (E) |
| `randrow(M)`, `randomrow(M)` | random matrix row | P (matrix mapping, M-21) |

`random(a,b)` with a comma is an *item pick*, not an interval — a classic trap; the parser MUST apply the `sp_random` rule (`sp.c:192–211`: first top-level `,` or `..`). The context matters (`parmprep`, `sp.c:351–380`): `random(a..b)` is rewritten to `randint` when the target is `\integer` and to `random` when it is `\real`; `randint`/`pickone` give an integer, or an item pick when a top-level comma is present (`sp.c:212`). Statistics: `randint` appears in 36 of 121 hand-written files; `shuffle` 26; `random` 21; `randitem` 4.

### 7.3 Expression language

- **REQ-EXPR-1** A table-driven expression parser (Pratt/precedence climbing) MUST be generated from a spec file (`expr_spec.json`, produced from `Lib/calc.c`/`evalue.c` function tables in the same way `oef_spec.json` is generated from the sources) rather than hand-coded.
- **REQ-EXPR-2** It MUST parse: numbers (including `1e-3`, decimals with `.`), `\var` references with `[…]` indexing, `+ - * / ^`, unary minus, parentheses, function calls, comparisons, `and or not`, string literals as they occur in OEF conditions, and the special calls of §7.2.
- **REQ-EXPR-3** Function mapping (E unless noted): `abs→ABS`, `sqrt→ROOT`, `ln→LN`, `log10→LOG10`, `exp→EXP`, `floor→ROUNDDOWN`, `ceil→ROUNDUP`, `rint→ROUND`, `pi→math_constant`, `%→math_modulo`, `min/max/gcd/lcm` → `math_on_list`/`gcd_lcm` over a `lists_create_with` (A). `evalue`, `diff`, `simplify` per M-23…M-25.
- **REQ-EXPR-4** **Trigonometry is a gap until the unit question (Q6) is answered.** WIMS `sin()` takes radians; the forward converter *assumed* degrees for XML `math_trig` (explicit hypothesis in `xml2oef/MAPPING.md:22` and `README.md`). Inventing a `×180/π` wrapper would be inventing logic (REQ-TODO-2). Therefore: with no `--trig-units` option, every `sin cos tan asin atan acos` call is **G-21** (placeholder + taint; file `partiel`). The option `--trig-units deg|rad` has **no default** and states the unit the **target platform**'s `math_trig` expects (OEF/WIMS arguments are always radians). When given: `rad` (the target platform uses radians) emits `math_trig` on the argument **unchanged**; `deg` (the target platform uses degrees) wraps the radian argument as `x × 180 / π` (`math_arithmetic`, `math_constant PI`) before `math_trig`. Special case, the forward-converter idiom `sin(x*pi/180)` (Appendix B.2): with `deg` the `*pi/180` factor is stripped and `math_trig` gets `x`; with `rad` the expression is kept as is. In all cases every trig block is reported at level `approximation`, `fidelite: non_verifiee`.
- **REQ-EXPR-5** Constant folding is allowed only when exact (integer arithmetic without division); never fold decimals.
- **REQ-EXPR-6** Anything the parser cannot parse becomes a gap (G-11/G-12) — never a best-effort partial tree.

`wims(<subcommand> …)` is the long tail: upstream 230 files / 2168 calls. The mapped set is the one `xml2oef` emits and therefore the only one with a known XML counterpart: `wims(replace internal X by Y in T)`→`text_replace`; `wims(lowercase|uppercase T)`→`text_changeCase`; `wims(charcnt T)`→`text_length`; `wims(char k of T)`→`text_charAt`; `wims(sort [numeric] items L)`→`lists_sort`; `wims(replace item number k by v in L)`→`lists_setIndex`. (Per-corpus use of `wims()`: hand-written 35/121 files = 29%, model templates 195/212 = 92%, all upstream 230/333 = 69%, generated 430/1100 = 39%; `slib()`: 11/121 = 9%, 91/212 = 43%, 102/333 = 31%, generated 0. Only six subcommands are mapped, so `wims()`/`slib()` are the main reason complete conversion is rare upstream, §14.2.) Everything else (`append`, `makelist`, `embraced`, `word`, `nonempty`, `items2words`, `values`, `select`, `record`, …) is **G-12**.

### 7.4 CAS calls

- `pari(…)` (hand-written: 11 files; generated: 89 files, 927 calls), `maxima(…)` (3 / 9 files), `yacas(…)`, `solve`, `int`, `det`: only the patterns in M-25…M-27 are mapped; the target platform CAS blocks use **Algebrite**, not PARI/Maxima, so even mapped calls are `A`. All others are **G-11**.
- `\function{f=…}` strings are kept as text (M-22) and compared by `type=function`/`formal` answers (§8).

### 7.5 LaTeX and HTML in statements

- LaTeX delimiters recognised: `\( \)`, `\[ \]`; `$…$` MUST NOT be assumed (it collides with price signs; 104 upstream files contain a `$…$` pattern that is mostly *not* LaTeX).
- Brace balancing: WIMS requires `() [] {}` balanced in the whole file, text included (`checkparentheses`); the tool MUST NOT "repair" unbalanced files — they fail the gate.
- Entities (`&#44;`, `&#36;`, `&euro;`, …, 90 upstream files) are kept verbatim in `TEXT`; the XML emitter escapes `& < >` once (no double escaping).
- Escapes: `\\` (literal backslash) and `\$`/`$` substitution (`$` → `&#36;` in `subst()`).

### 7.6 Images and files

- `<img src="\imagedir/x.png">`, `\imagedir`, `\filedir`: map to `image{url}` with the relative path preserved; record each in the report (`assets[]`); `--assets-dir DIR` copies referenced files that exist next to the OEF (never downloads).
- `draw(…)`/`canvasdraw`/flydraw output URLs are not images in XML terms (G-09).
- `\special{imageinput|imagefill|drawinput|…}` is G-07.

---

## 8. Answer types and their evaluation

### 8.1 Directives

`\answer{prompt}{expected}{option=…}{type=…}` (alias `\reply`, directive table `oef2wims.c:61–115`) — up to 5 parameters; `type=`, `option=`/`options=` and `weight=` are recognised *in any parameter position* (`p_answer`, `process.c:227–`); a prompt of 40 characters or more is an **error** (`Answer prompt too long`, `process.c:293`); a `type=` not in the 49-entry table (`process.c:173–221`) is passed through as `replytype=<value>` (the tool treats it as G with the raw value in the report). `\choice{prompt}{good1,good2}{bad1,bad2}{option=…}{weight=…}` (`p_choice`, `process.c:354–`) has **no `type=`** parameter (an upstream `type=` there is not interpreted: the 7 upstream `\choice` files have none), and its over-long prompt is truncated without error. `\answer` whose expected value is a `\name` that is **not yet defined** is an *analysed answer* (`replygood=?analyze n`): the expected value is then computed by `\condition`s (G-15).

### 8.2 Type table (planned class; counts = files / occurrences)

**Classes.** `D` = structurally direct (the XML block shape is known from real files), `A` = approximate, `G` = gap. **In the report every question mapping is at best class `A` for fidelity until Q5 is answered** (REQ-REP-7): numeric/radio/checkbox/correspond/reorder are marked **A†** below, meaning *structure direct, grading semantics unverified*. The D/A/G split used by the corpus statistics (Appendix A.2) is the structural one. Upstream counts: all 333 files (hand-written subset in brackets). Generated counts: files.

| OEF `type=` | WIMS evaluation | XML target | Class | Upstream files [hand-written] | Gen. files |
|---|---|---|---|---:|---:|
| `numeric`, `number` | numeric comparison within `\precision` | `question_open{type=decimal}` (`integer` when the expected value is provably an integer, `fraction` when written `a/b`) | A† | 23 [11] | 581 |
| `default`, *(none)* | text/number default compare | `question_open{type=string}` | A | 14 [14] | – |
| `case`, `text` | exact string, case-sensitive | `question_open{type=string}` | A | 18 [1] | 28 |
| `nocase`, `atext`, `chset`, `raw` | case-insensitive / any-of / raw | `question_open{type=string}` | A | 6 [6] | – |
| `formal`, `algexp`, `expalg`, `numexp`, `function`, `equation`, `litexp`, `symtext` | symbolic / numeric-expression equivalence | `question_open{type=expression}` | A | 20 [20] | 50 |
| `radio` | one choice among a list | `question_multiple_choices{type=unique}` | A† | 8 [8] | 301 |
| `checkbox` | several correct | `question_multiple_choices{type=multiple}` | A† | 20 [9] | 15 |
| `menu`, `select` | drop-down choice | `question_multiple_choices{type=unique}` | A | 11 [4] | – |
| `correspond`, `corresp` | association | `question_associate{solution1,solution2}` | A† | 14 [4] | 51 |
| `reorder` | ordering | `question_reorder{solution}` | A† | 2 [2] | 23 |
| `click`, `mark`, `clickfill`, `dragfill`, `multipleclick`, `puzzle`, `flashcard`, `crossword`, `coord`, `jsxgraphcurve`, `chemdraw`, `jmolclick`, `vector`, `matrix`, `set`/`aset`/`fset`, `time`, `units`/`sigunits`, `draw`, `code`, `compose`, `clicktile`, `clock` … | interactive / module-defined | none | **G (G-06)** | 209 [54] files with ≥ 1 G answer (union with the next row) | 0 |
| dynamic (`type=\var`) | decided at run time | none | **G** (REQ-IN-7) | 74 [10] | 0 |

True/false: OEF has none; a `radio` whose only two options are the language's true/false pair MAY map to `question_true_false` (A; `solution` is a boolean) — otherwise `question_multiple_choices`.

### 8.3 Question block construction (REQ-MAP-Q-TEMPLATE)

- Each converted `\answer`/`\choice` becomes **one question block in the main chain, in OEF order** (`ansorder`), preceded by the `display_element` carrying the statement text that precedes its `\embed` marker.
- `text` input ← prompt/statement fragment (richtext); `solution` input ← expected value (E for literal/variable values); for choice types `solution` = `lists_create_with` of right items and `proposals` = `lists_create_with` of wrong items; `nb_proposals_to_display` MAY be omitted (unknown semantics).
- Fields and `extraState` are copied from the **modal real shape** per type (e.g. `question_open`: `type`, `moreOptions=true`, `mutation_shape=value`, `answer` (QUESTION variable id), `question`, `default_feedbacks=true`, `raw_options={}`; extraState `displaymoreOptions`, `statement`). Their semantics are **not confirmed** (Q5), so templates live in one data file (`templates/question_*.json`) that can be corrected without touching code.
- Student-answer variables (`answer`, `question` fields) are declared in `<variables>` with `type="QUESTION"` as in real files.

### 8.4 Options and weights

`option=` tokens (upstream occurrences): `noanalyzeprint` 186, `shuffle` 117, `nonstop` 82, `noorder` 50, `text` 50, `detag` 40, `show` 25, `split` 21, `sort` 14, `multiple` 3, `eqweight` 3, `absolute` 2. Handling: `shuffle` on choice types → `info` (the target platform shuffling behaviour unknown); `noorder` on `checkbox`/`correspond` → `info`; **all others and `weight=` → G-05** (reported at level `approximation` on the question, since they change grading or display).

### 8.5 Evaluation, conditions, feedback

- `\feedback{condition}{message}` (upstream: 38 files; generated: 505) → phase 3: `feedbacks` input of the question (`controls_if` + `display_element`), reversing the forward rule ("`\feedback{condition}{message}` ← `feedbacks`, `context_question`, `feedback_global`").
- `\condition{prompt}{cond}`/`\conditions{…}` (24 + 14 files) → phase 3: answer predicate (`raw_options {"callbackSolution":true}` as seen in 128 real `question_open`) *only* for the patterns the forward converter emits (`\x2orepN` + `\condition`). Others stay G-15.
- `\sc_replyN` (score of answer N), `\replyN` → inside feedback conversion only (`is_solution_found{solution_found_type}`).
- The evaluation *semantics* of the target platform (how `decimal` compares, tolerance, attempts, whether `unique`/`multiple` grade like `radio`/`checkbox`) are not documented in the material; every converted question is reported `fidelite: non_verifiee` (REQ-REP-7) unless a verified rule exists (Q5). This is why §8.2 marks even the structurally direct types A†.

---

## 9. Multi-step exercises

- OEF: `\steps{1,2,3}` declares steps (at most one per file), `\nextstep{…}` computes the next step from the answers, `\step` is the current step number; each step re-runs the statement, hint and answers. Upstream: `\steps` in 101 files (30%; hand-written 8), `\nextstep` in 36 (hand-written 11), `\step` referenced in 47.
- The target platform has no step construct; its multi-question mechanisms are *sequential question blocks*, `context_question`, nested questions in `feedbacks` (`settings/hasNestedQuestion`) and `versions` (difficulty variants, a different concept).
- **REQ-STEP-1** *Static* steps (the `\statement` contains `\if{\step=k}{…}` or `\ifval` branching on `\step`, with a fixed `\steps` list and a trivial `\nextstep`) MAY be linearised into consecutive display/question blocks in phase 3 (A). A question active in k steps is emitted k times; the report records `copies(q)=k` and the counters of REQ-REP-4 (I2, I3) stay valid because they count source questions, not output blocks.
- **REQ-STEP-2** *Dynamic* progression (`\nextstep` depends on the answers) is **G-08** — placeholder + taint; never approximated.
- **REQ-STEP-3** Until phase 3 every file containing `\steps` is `partiel` (or `echec` under `--strict`) with the gap listed.

---

## 10. Languages

- XML `lang/@code` ∈ {fr, en, es, it, de, ar} (schema). OEF `\language{xx}`: upstream: fr 38, it 10, es 1, en 1, **ca 1**, dynamic 3; generated: fr 1032, en 48, de 13, it 6, ar 1. Only 54 of 333 upstream files declare a language at all.
- **REQ-LANG-1** `\language` in the six codes → `info.default_lang` + one `<lang code=…>` element with `<title>` = `\title` **and a `<description>` that is always present**: its text is `\description` when the OEF has one, otherwise an **empty `<description/>`** (the schema requires the element, RNG lines 93–94; upstream OEF has no `\description` in any of 333 files). Proof by fixtures: `valid/minimal_info_chain.xml` validates with an empty `<description/>`, `invalid/lang_missing_description.xml` fails (§13.1).
- **REQ-LANG-2** `ca cn nl si` and dynamic values: G-04 — fall back to `--default-lang`, report. The schema is NOT widened by this tool (schema change request SC-2, §17.2).
- **REQ-LANG-3** No `\language`: use `--default-lang` (default `fr`), level `info`.
- **REQ-LANG-4** Right-to-left (`ar`) text is copied unchanged; no bidi processing; XML is UTF-8.
- **REQ-LANG-5** Text content is never translated by the tool.

---

## 11. Architecture

### 11.1 Language choice

**Python 3.12** (the owner's language; installed on the Windows PC; same language as `oef_validate.py`, `oef_llm_fix.py`, `oef2html.py`). The existing XML→OEF converters are **Go** (single static `xml2oef.exe`, no dependency) and **JavaScript** (browser + Node). Trade-offs:

| | Python 3.12 (proposed) | Go (like `xml2oef`) | JS |
|---|---|---|---|
| Owner maintains it | yes | harder | partly |
| Reuse `oef_validate.py`/`oef_spec.json` | direct | port | port |
| Single exe for Windows | PyInstaller (optional) | native | n/a |
| XML validation (RNG/XSD/Schematron) | `lxml` | no native RNG/XSD; libxml2 via cgo breaks the static build | external |
| Speed | sufficient (median 12 directives/file hand-written, 48 generated) | best | – |

**Decision (closed 2026-11-10): Python 3.12**, standard library + `lxml` (optional extra for validation). Reasons beyond the table:
- Go cannot validate RNG/XSD natively; linking libxml2 via cgo removes the "single static exe" advantage, while `lxml` does it today.
- Little code is shared with the forward converter: the overlap (mapping tables, block catalogue, templates) is kept as data files (`mapping.yaml`, `templates/*.json`, REQ-ARCH-2) that any language can read.
- The round-trip tests call `xml2oef.exe` as a separate program, so mixing Python and Go costs nothing.
- Speed is not a constraint (about 1,400 files).

Distribution (Q11, closed): Python 3.12 + `lxml`; an optional PyInstaller one-file `oef2xml.exe` bundling `lxml` in phase P4. Go is reconsidered only if the tool must run on machines without Python **and** the PyInstaller exe is not acceptable there.

### 11.2 Pipeline

```
 .oef ──decode──► lexer ──► parser ──► OEF AST ──┬──► semantic pass ──► IR ──► emitter ──► .xml
   │               (find_matching,   (directives,  │     (types of vars, taint,   (XML blocks,    │
   │                oef2wims rules)   phases)      │      pre/post, steps, gaps)   ids, templates)  ▼
   └──► gate: oef2wims (-v2/-log) ──► .def (optional cross-check)            report.json / .tsv
                                                          ▲
                              xml validation (RNG, XSD, Schematron) + shape lint ──┘
```

1. **Lexer/parser** — a port of `process()`: top-level directives, parameter counts from a spec file (`oef_spec.json`, generated from the C source), transparent bodies for `\if \ifval \for \while`, source positions (line/column) on every node. Share this module with `oef_validate.py` (one parser for lint and migration).
2. **OEF AST** — directives with raw parameter text and positions; nothing interpreted yet.
3. **Semantic pass → IR** — typed definitions (`int/real/text/list/matrix/function`), pre/post phase, use-def graph, **taint**, expression trees, statement fragments (text, variable refs, LaTeX, HTML spans, `\embed`), questions with resolved `replytype` (using the `.def` when available), gap nodes with reason and original text.
4. **Emitter** — IR → XML program using `templates/*.json` (block shapes from the catalogue), the deterministic id generator, the variable table, and the placeholder writer. Streaming `lxml.etree`/`xml.etree` with a fixed attribute order.
5. **Report builder** — counters maintained by the IR (REQ-REP-4 invariant).
6. **Gates** — `oef2wims` before (syntax), RNG/XSD/Schematron + shape lint after.

- **REQ-ARCH-1** The IR is serialisable (`--dump-ir`, JSON) and the CLI offers `--dump` (pseudo-code like `xml2oef -dump`) for debugging.
- **REQ-ARCH-2** Mapping rules live in data (`mapping.yaml`/`templates/`), not scattered in code, so the spec table (§6) and the code share ids (`M-nn`, `G-nn`); each report detail cites its id.
- **REQ-ARCH-3** No network access, no LLM calls in the converter. (An optional separate `--llm-assist` is explicitly out of scope.)
- **REQ-ARCH-4** **oef2wims as syntax gate**: use the owner's `oef2wims-log.exe` / `oef2wims-v2.exe` wrappers (E2 build: handle Unicode and long paths; the plain reference `oef2wims.exe` fails on non-ANSI paths). Command: `oef2wims-v2.exe --json <file.oef>`. **Behaviour verified in `oef2wims_v2.c`** (identical copies: `/workspace/oefc/e2pkg/E2_build/sources/v2/` and repo `validation/oef/oef2wims/sources/v2/`): the wrapper needs `oef2wims.exe` beside it; it writes `<name>.def`, `<name>.log` and `<name>.trace` **next to the input file** (`run_one`, line 195–196: `swap_ext(…, L".log")`, `L".def"`); with `--json` it writes **`<name>.json` next to the log file, not on stdout** (`swap_ext(jsw,logw,L".json")`, line 196; JSON built at line 303; usage text line 350: "écrit aussi nom.json"); in batch mode it also writes `oef2wims-batch.json` (lines 365–367); `--log FILE` moves the log and therefore the JSON (line 393). The plain `-log` wrapper (`oef2wims_log.c`) has **no `--json` option**. Consequences: the gate MUST run on a **temporary copy** of the OEF in a scratch directory (so that no `.def/.log/.trace/.json` pollutes the input folder), then **read `<scratch>/<name>.json`** (not stdout) and delete the scratch files unless `--keep-gate-files`; the exit code is the compiler's return code (usage errors return 2). Fall back to the validator when the exe is absent (`--gate validator`). A gate failure is `echec` with the compiler's line/column and message copied. Because `oef2wims` ignores unknown top-level commands and truncates at 1024 directives, the gate is necessary but not sufficient — the tool's own parser MUST additionally warn on both.
- **REQ-ARCH-5** Suggested layout. The existing `validation/` tree of the repository (OEF validator, compiler wrappers, schemas v1, schema fixtures of §13.1) MUST be kept; converter code is added next to it:
  ```
  OEF2XML/
    docs/CAHIER_DES_CHARGES_OEF2XML.md
    validation/{oef/oef_validate,oef/oef2wims,xml/schemas_v1,xml/tests}   # existing, unchanged layout
    src/oef2xml/{cli,decode,lexer,parser,ir,semantic,expr,emit,templates/,report,gate,validate}.py
    spec/{oef_spec.json,expr_spec.json,mapping.yaml,xml_block_catalog.json}
    schemas/            # v2 copies when supplied (v1 stays under validation/xml/schemas_v1)
    tools/{oef_corpus_stats.py,scope_bounds.py,xml_block_catalog.py,roundtrip.py}
    tests/{unit,fixtures,golden,roundtrip}/
  ```

---

## 12. CLI, batch, Unicode paths, Windows

### 12.1 Command line

```
oef2xml [options] INPUT...        INPUT = .oef file or directory
  -o, --out DIR                   output folder (default ./oef2xml_out)
  -r, --recursive                 recurse into directories
  --report FILE.json              conversion report (§4.4)
  --csv FILE.tsv                  one line per file
  --encoding auto|utf-8|latin-1|cp1252
  --default-lang CODE             fr (default) en es it de ar
  --max-attempts N                info.max_attempts (default 1)
  --source-format ir|json|yaml|xml   (default ir; no 'oef' value in the schema)
  --id-from stem|hash             program id (default stem)
  --gate oef2wims|validator|none  syntax gate (default oef2wims if found)
  --oef2wims PATH                 path to oef2wims-v2.exe / oef2wims-log.exe
  --def FILE|DIR                  precompiled .def files (optional cross-check)
  --validate rng,xsd,sch|none     validate outputs (default rng,xsd; sch if --schematron FILE)
  --schema-dir DIR                folder with the .rng/.xsd/.sch to use
  --strict                        any partial file becomes a failure
  --html pass|strict              raw HTML in text blocks: carry verbatim (default) or placeholder
  --trig-units deg|rad            no default: without it trigonometry is a gap G-21 (REQ-EXPR-4)
  --strict-limits                 1024-directive cutoff becomes a failure (REQ-IN-5)
  --placeholder-carrier text|display_element   block type of TODO placeholders (default text, REQ-TODO-1)
  --idioms on|off                 recognise forward-converter idioms (default on, §6.6)
  --schematron FILE               run this Schematron (Q1)
  --keep-gate-files               keep the scratch .def/.log/.json of the gate (REQ-ARCH-4)
  --mdef NAME[,NAME]              module macro names (oef2wims_mdef)
  --assets-dir DIR                copy referenced image files
  --jobs N                        parallel files (default 1; deterministic output regardless)
  --dump | --dump-ir              pseudo-code / IR JSON for one file
  -q/--quiet, -v/--verbose, --version
```

Exit codes: `0` all `complet`, `1` ≥ 1 `partiel`, `2` ≥ 1 `echec`, `64` bad usage.

### 12.2 Batch behaviour

- **REQ-BATCH-1** Failure of one file never stops the batch (`--fail-fast` opt-in). A crash in a file becomes an `echec` entry with the exception, never a lost entry.
- **REQ-BATCH-2** Output names `<stem>.xml` (`--suffix` e.g. `_OEF2XML_v1` to match the pipeline convention `ID_CODEX_v1.xml`); never overwrite originals; refuse to write into the input folder unless `--force`.
- **REQ-BATCH-3** Per-file `<stem>.check` log (gate output, validation messages) like the existing pipeline, plus the batch `Validation_AllSchemas.csv`-style TSV.

### 12.3 Unicode paths and Windows 11

- **REQ-WIN-1** Runs on Windows 11 (Python 3.12 from `py -3.12`) and Linux. Paths handled with `pathlib` (wide-character APIs): `数学`, `Συνάρτηση`, `test_😀`, `été`, spaces and paths > 260 characters (add the `\\?\` prefix; the PC has `LongPathsEnabled=0`).
- **REQ-WIN-2** All text I/O is explicit UTF-8 (`encoding="utf-8"`), `PYTHONUTF8=1` set for child processes; console output reconfigured to UTF-8 (`sys.stdout.reconfigure`) so non-cp1252 names do not crash printing.
- **REQ-WIN-3** External programs (`oef2wims-v2.exe`, `oef2wims-log.exe`) are launched with `subprocess` using a list of arguments (no shell) and a Unicode-safe environment. The E2 wrappers handle short-name/temp-copy modes; the plain `oef2wims.exe` is **not** supported for non-ANSI paths.
- **REQ-WIN-4** Default tool locations are configurable, with documented defaults on the owner's machine: schemas `D:\ALF_Scripts\00-Schemas\03-xml_IR`, compiler `D:\ALF_Scripts\00-Schemas\01-oef_WIMS\01-oef_WIMS_CheckC\oef2wims-v2.exe` (never hard-coded in the source; read from a `oef2xml.toml` or environment variables).
- **REQ-WIN-5** A `tests/unicode` suite reuses the E2 cases (`数学`, `Συνάρτηση`, `test_😀`, 285-character path, spaces, `été`) for input paths, output paths and `--assets-dir`.
- **REQ-WIN-6** Optional, phase P4: PyInstaller one-file `oef2xml.exe` bundling `lxml` (not required for the MVP; Q11 closed, §11.1).

---

## 13. Validation and round-trip tests

Four gates apply to every file, in this order. **G0** decode and parse; **G1** compile gate on the *source* OEF (`oef2wims`, REQ-ARCH-4); **G2** schema validation of the *output* (RNG + XSD, plus Schematron when supplied) and shape lint; **G3** internal invariants (REQ-REP-4) and placeholder lint (REQ-TODO-6).

### 13.1 Schema validation and the schema fixtures

- **REQ-VAL-1** Every output XML is validated against `XML_program_v1.rng` **and** `XML_program_v1.xsd` (`lxml.etree.RelaxNG` / `XMLSchema`); the report records `rng`, `xsd` as `ok`/`ko` with the first error. Both schemas are required to agree; a disagreement is an internal error.
- **REQ-VAL-2** Schematron: conditional on Q1. Without the `.sch` the report says `schematron: non_execute` and AC-4 is not evaluated; with it (`--schematron FILE`) every document is checked and R05 behaves as in REQ-TODO-4.
- **REQ-VAL-3** **Shape lint** (REQ-SCH-4) on the written XML: every block type is in the whitelist, every field/input/`extraState` name is in `xml_block_catalog.json`, children order is as in §2.3 item 7, every `variables_get/set` id is in `<variables>`.
- **REQ-VAL-4** **Schema fixtures** (committed in `validation/xml/tests/`, run with `python3 run_schema_tests.py`). They pin the schema behaviour the converter relies on, so that a schema change (e.g. v2) is detected immediately:

| Fixture | Expected | Requirement it protects |
|---|---|---|
| `valid/minimal_info_chain.xml` | valid in RNG **and** XSD | `info` → `variables_set` → `display_element` chain (REQ-OUT-4); **orphan top-level `text` placeholder with a comment icon** (REQ-TODO-1); `<lang>` with an **empty `<description/>`** (REQ-LANG-1) |
| `invalid/source_format_oef.xml` | invalid in both | `source_format="oef"` is not allowed (REQ-SCH-5, SC-1) |
| `invalid/lang_ca.xml` | invalid in both | `lang/@code="ca"` is not allowed (REQ-LANG-2, SC-2) |
| `invalid/lang_missing_description.xml` | invalid in both | `<lang>` without `<description>` is invalid (REQ-SCH-7) |

  The runner `validation/xml/tests/run_schema_tests.py` (Python 3 + `lxml`) validates each fixture against both schemas, expects `valid/` to pass and `invalid/` to fail in both, and exits non-zero otherwise (0 = all expectations met, 1 = at least one not met, 2 = setup error). Result when run on 2026-11-09: **8/8 expectations met, exit code 0** (4 fixtures × 2 schemas); a negative control (an invalid file copied into `valid/`) made the runner exit 1. The runner is part of CI (§13.5) and of AC-3.

### 13.2 Compile gate (G1) tests

- **REQ-VAL-5** G1 runs `oef2wims` on every source OEF (REQ-ARCH-4). Expected: the 333 upstream files compile except the files refused by the compiler (AC-2); all 1100 generated files compile (the pipeline reports 1100/1100). The tool's own parser MUST agree with the compiler on accept/refuse for 100% of these 1433 files (AC-1); every disagreement is a defect of the parser or of the gate wrapper.
- **REQ-VAL-6** Re-generated OEF (round trip, §13.3) is compiled with the same gate (level T0).

### 13.3 Round-trip tests and evaluation sets

The forward converters are the only available oracle for "the XML means something", but they cover only machine-written OEF. v0.2 therefore defines **three round trips** with an explicit metric, and a **hand-written evaluation set**.

**Notation.** `O` = an OEF file; `X = oef2xml(O)`; `O' = xml2oef(X)` with the existing Go `xml2oef` (unmodified); `N(·)` = the normalisation below.

**Normalisation `N` (applied to both sides before comparing OEF text):**

| Rule | Operation |
|---|---|
| N1 | decode UTF-8; line endings LF; strip trailing whitespace; drop leading/trailing blank lines; collapse runs of blank lines |
| N2 | count, then delete, `%%` comment lines (forward markers `x2o NON TRADUIT` / `x2o approximation` are counted separately, REQ-IDIOM-1) |
| N3 | rename temporaries `\x2oN`, `\x2orepN` to `\x2o1, \x2o2, …` in order of first occurrence |
| N4 | order of header directives (`title`, `language`, `author`, `description`) is not significant |
| N5 | whitespace inside expressions (outside text values) is not significant (`a + b` ≡ `a+b`) |
| N6 | entity spelling canonicalised (`&#x2c;` → `&#44;`); no entity is decoded |
| N7 | `\statement`: token stream after collapsing whitespace; `<br/>` ≡ `<br>` |
| N8 | order of `\answer`/`\choice` and of definitions is significant (never sorted); number and `type=` of answers compared exactly |

**Verdict per file:** `IDENTICAL` (equal after N1–N8) · `DIFF-EXPLAINED` (every differing line is covered by a reported `approximation` or gap detail of the same file) · `DIFF-SILENT` (any other difference). **A `DIFF-SILENT` file is a defect, whatever the thresholds below.**

#### RT-A — fixed point on the generated corpus (Gn, 1100 files)

`O1` ∈ the 1100 generated OEF → `X1 = oef2xml(O1)` → `O2 = xml2oef(X1)`; compare `N(O1)` with `N(O2)` (the 1116 `xml_etudes` programs are the ancestors of `O1`; the 16 programs for which `xml2oef` wrote no OEF are not part of RT-A). Thresholds, measured on files for which `oef2xml` did not return `echec`:

| Subset | Metric | Target | PASS | FAIL |
|---|---|---|---|---|
| the 465 files without `x2o NON TRADUIT` marker that are within scope (`scope_bounds.py`, §14.2) | share `IDENTICAL` | ≥ 85% | ≥ 70% | < 70% |
| the 634 files **with** markers | every marker line is reported as G-22 | 100% | 100% | < 100% |
| the 634 files with markers | share `IDENTICAL` on `N(O)` minus marker-covered lines | ≥ 70% | ≥ 50% | < 50% |
| all | share `DIFF-SILENT` | 0 | 0 | any |

#### RT-B — hand-written OEF (evaluation sets)

The generated corpus says nothing about how people write OEF (§2.2), so RT-A alone is not accepted as evidence. Evaluation sets:

- **E-H** — the **121 upstream hand-written files** (104 class sources + 17 module files). Automated checks on all 121 (B1, B2) and a **manual review** of a stratified sample (B3).
- **E-M** — the **212 model templates**, automated checks only (B1, B2): they are template generators, not exercises (§2.2).
- **E-O** — the owner's own hand-written OEF, **to be supplied** (Q2). Until then E-H is the only hand-written evidence; when E-O arrives it is added with the same protocol and AC-10 is re-evaluated.

| Step | Content | Pass criterion |
|---|---|---|
| B1 | `oef2xml` on the set; status distribution; RNG+XSD; shape lint; invariants I1–I3 | the per-corpus thresholds of §14.2; schema/lint/invariants 100% |
| B2 (T0) | `O' = xml2oef(X)` compiled by `oef2wims` for every file with ≥ 1 converted question | ≥ 95% compile; each failure triaged as converter defect or forward-converter limit |
| B3 (manual) | owner (or delegate) reviews **30 files** of E-H, stratified so that every answer class of §8.2 (numeric, string, expression, choice, correspond/reorder) and every gap family G-03…G-15 occurs at least once; checklist: **C1** statement faithful, **C2** variables and ranges faithful, **C3** expected answers faithful, **C4** answer types faithful, **C5** every gap listed with id and verbatim fragment, **C6** no invented logic | ≥ 24 of 30 (80%) pass C1–C6; **0** file with invented logic (C6) — hard |
| B4 (T1) | structural equality of `O` and `O'`: counts of variables, answers, choices, types, order | reported, no threshold (hand-written OEF is outside the forward converter's vocabulary) |

Comparison levels beyond text: **T0** compiles; **T1** structure equal; **T2** with a seeded `wims.cgi`, same seed → equivalent statement and expected answers; **T3** grading equivalence on a set of right/wrong student answers. **T2 and T3 are conditional** on a runnable WIMS with seeding (not on the box) and are not part of any acceptance criterion in v0.2.

#### RT-C — idempotence

`X1 = oef2xml(O)`; `O1 = xml2oef(X1)`; `X2 = oef2xml(O1)`; `X1` and `X2` MUST have the same block structure (ids are derived from `sha1(program id + structural path)` so equal structure gives equal ids). Also, two runs of `oef2xml` on the same input are byte-identical (REQ-OUT-3). Target and PASS: 100% of files with status `complet` in RT-A; FAIL otherwise.

### 13.4 Unit and golden tests

- Lexer/parser: golden AST for each of the 10 sample files of the validator (`validation/oef/oef_validate/tests/samples/`) and for 30 hand-picked upstream files (comments, nested braces, `\if` bodies, `random(a,b)` vs `random(a..b)`, CRLF, ISO-8859-1).
- Expression parser: table-driven tests generated from `expr_spec.json`; one test per special function of Appendix A.3.3 (mapped, gap, or tainted).
- Emitter: golden XML for each mapping row `M-nn`, each checked by §13.1 and the shape lint.
- Reports: golden JSON for one `complet`, one `partiel`, one `echec` file per phase.

### 13.5 Continuous integration

Python 3.12 on Windows 11 and Linux; jobs: unit and golden tests, `run_schema_tests.py`, the 10 validator samples, RT-A on a fixed 100-file sample (full run nightly), the Unicode suite (REQ-WIN-5). `oef2wims` is available only on Windows (E2 wrappers) or via the Linux build; jobs needing it are skipped, not failed, when it is absent, and the skip is printed.

---


## 14. Acceptance criteria

Every criterion is checkable by a script and states its evidence. Statements about importability or exactness are **excluded** until Q5 is answered (REQ-SCH-6, REQ-REP-7).

### 14.1 Criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-1 | The tool's own parser agrees with the `oef2wims` compile gate (accepted / refused) on all 1433 files of the corpus (333 upstream + 1100 generated). | G1 run, §13.2 |
| AC-2 | The upstream files the compiler refuses are reported `echec` with the compiler's message and position and no XML. Expected: **2 files**, `00286` and `00307` (model templates `numdata.oef`, `menutext.oef`; no `.def` was produced for them on the box). **To be confirmed by the first G1 gate run** — the count of 2 comes from the validator's README and a check of the missing `.def` files, not from a run of the new tool. | G1 run |
| AC-3 | `validation/xml/tests/run_schema_tests.py` exits 0 (8/8 expectations: the valid fixture passes RNG and XSD, the three invalid fixtures fail both), **and** 100% of the XML files written by the tool for non-`echec` inputs validate in RNG and XSD. | §13.1 |
| AC-4 | **Conditional on Q1.** When the v2 Schematron is supplied: every file reported `complet` passes it; every file with no question block fails R05 and is never `complet`. When it is not supplied: the tool's own `aucune_question` flag (REQ-TODO-4) is raised on 100% of the zero-question outputs and `schematron` is reported `non_execute`. | §13.1 |
| AC-5 | Shape lint: 0 emitted block types outside the whitelist (190 enum values minus the 21 never observed), 0 field/input/`extraState` names outside the catalogue. | REQ-VAL-3 |
| AC-6 | Determinism: two runs give byte-identical XML and report on the whole corpus. | REQ-OUT-3 |
| AC-7 | Invariants I1, I2, I3 hold on 100% of files (REQ-REP-4). | G3 |
| AC-8 | **No invention, no silent loss**: 0 file `complet` that contains a dynamic type, an unconverted trig call without `--trig-units`, a G-22 marker or any placeholder; placeholder lint passes on 100% of `partiel` files (REQ-TODO-6); 0 `DIFF-SILENT` in RT-A/RT-B. | G3, §13.3 |
| AC-9 | **Status shares per corpus** meet §14.2 (hand-written 121, model templates 212, generated 1100). | §14.2 |
| AC-10 | Round trips: RT-A thresholds (§13.3) met; RT-B on E-H: B1–B3 criteria met (≥ 24/30 reviewed files, 0 invented logic); RT-C 100%. Re-evaluated when E-O is supplied (Q2). | §13.3 |
| AC-11 | Windows 11: the Unicode suite of REQ-WIN-5 passes for input paths, output paths and `--assets-dir`; no output file is written next to an input unless `--force` (REQ-BATCH-2); the gate leaves no `.def/.log/.trace/.json` in the input folder (REQ-ARCH-4). | tests/unicode |
| AC-12 | Report and exit codes: JSON and TSV have all fields of REQ-REP-2/5; exit codes `0/1/2/64` as REQ-REP-6; `fidelite` present on every file and no file is `exacte` while Q5 is open. | golden reports |
| AC-13 | Licence: the repository has a `LICENSE` consistent with the decision of Q7 before the first code commit. | repo |

### 14.2 Target shares of `complet` / `partiel` / `echec` per corpus

**Why a target per corpus.** The three corpora behave very differently (§2.2), and an aggregate percentage would be dominated by whichever is largest. Each corpus has its own **upper bound** (computed by `scope_bounds.py`, reproducible, Appendix C.1), a **target**, a **PASS** threshold (acceptance) and a **FAIL** condition.

**How the bounds are computed.** A file is *complet-eligible* if every construct it uses lies inside the final planned scope (§6, §7, §8 after phase 3): directives of the header/definition/control/answer families (hint/help/solution, steps, `\plot`, `\latex`, `\mdef`, `\special` excluded), answer types of classes D/A of §8.2 (no interactive, no dynamic type), special functions of §7 (no `draw`, `slib`, `solve`, `int`, `det`, …; `pari`/`maxima` only for the forward-converter patterns, i.e. for the generated corpus), `wims()` subcommands among the six mapped ones (§7.3; for the generated corpus all, since the forward converter emits them), `\condition` only for the forward-emitted pattern (generated corpus), and — generated corpus only — no `%% x2o NON TRADUIT` marker (REQ-IDIOM-1). A file is *question-eligible* if it has at least one convertible `\answer`/`\choice` and no dynamic type. Both are **upper bounds**: they ignore taint, expression-parsing failures and anything invisible at directive level. A tool that reports *more* `complet` files than the bound has a false positive or the bound is wrong: either way it is a FAIL until explained.

**Why the bounds differ so much.** `wims()` appears in 35/121 hand-written files (29%), 195/212 model templates (92%), generated 430/1100 (39%); `slib()` in 11/121 (9%), 91/212 (43%), generated 0; only six `wims()` subcommands and no `slib()` module have an XML counterpart. Hand-written exercises also use interactive answer types (54 of 113 files with an `\answer` have at least one), `\special` (46 files), `draw()` (25), `\hint` (14), `\nextstep` (11). The model templates are template generators: 74 files use a dynamic answer type and 155 of 212 have no convertible question at all. The generated set only uses the forward converter's vocabulary, but 634 of 1100 files carry a marker for a block that was lost upstream.

**Definitions.** `C` = files `complet`; `Q` = files with ≥ 1 *converted* question (`questions_converties ≥ 1`, whatever the status); `E` = files `echec`; `partiel` = N − C − E. Among `partiel` files, those with no converted question (figure-only exercises, all-dynamic templates) will be flagged `aucune_question` (REQ-TODO-4).

| Corpus | N | Metric | Upper bound | Target | **PASS** | **FAIL** |
|---|---:|---|---|---|---|---|
| **H** — upstream hand-written (104 class + 17 module) | 121 | `C` complet | 19 (16%) | ≥ 16 (13%) | ≥ 12 (10%) | < 12, or > 19 unexplained |
| | | `Q` ≥ 1 converted question | 70 (58%) | ≥ 56 (46%) | ≥ 49 (40%) | < 49 |
| | | `E` echec | 0 | 0 | ≤ 2 (1.7%) | > 2 |
| | | expected `partiel` at target | | 105 (87%) | ≤ 109 (90%) | > 109 |
| **M** — upstream model templates | 212 | `C` complet | 4 (2%) | ≥ 3 (1.4%) | ≥ 2 (0.9%) | < 2, or > 4 unexplained |
| | | `Q` ≥ 1 converted question | 57 (27%) | ≥ 46 (22%) | ≥ 40 (19%) | < 40 |
| | | `E` echec | 2 (the compiler refusals, AC-2) | 2 | ≤ 4 (1.9%) | > 4, or any compiler refusal not reported `echec` |
| | | expected `partiel` at target | | 207 (98%) | ≤ 210 | > 210 |
| **Gn** — generated by `xml2oef` | 1100 | `C` complet | 465 (42%) | ≥ 395 (36%) | ≥ 325 (30%) | < 325, or > 465 unexplained |
| | | `Q` ≥ 1 converted question | 973 (88%) | ≥ 830 (75%) | ≥ 780 (71%) | < 780 |
| | | `E` echec | 0 | 0 | ≤ 11 (1%) | > 11 |
| | | expected `partiel` at target | | 705 (64%) | ≤ 775 (70%) | > 775 |
| *U — all upstream (H + M), information only* | 333 | `C` / `Q` bounds | 23 (7%) / 127 (38%) | sum of H and M targets | sum of H and M PASS | — |

Expected shares at target (`complet` / `partiel` / `echec`): **H** 13% / 87% / 0%; **M** 1.4% / 97.6% / 0.9%; **Gn** 36% / 64% / 0%. `partiel` is the *normal* outcome for upstream OEF: it means "converted as far as possible, the rest isolated and listed", which is the purpose of the tool (§1.2).

**Rules that apply to every corpus (hard, no threshold):** 0 crash; 100% of files accounted for in the report (REQ-BATCH-1); 0 `complet` file containing a placeholder, a dynamic type or a G-22 marker (AC-8); 0 `DIFF-SILENT` (§13.3); every `echec` carries the message of the failing gate.

**Phase gates.** The shares above are for the end of phase 3 (§15). The **MVP gate (end of phase 1)** uses the phase-1 scope `M1` (`oef_corpus_stats.py`, tier `M1_mvp_scope`: header, `\integer \real \text`, `randint/random/shuffle/randitem/item/items`, answer types numeric/case/formal family/radio/checkbox): files wholly inside `M1`: **H 5, M 0, Gn 324**. MVP PASS: ≥ 80% of the `M1` files of H and of Gn reach `Q ≥ 1` (H ≥ 4 of 5, Gn ≥ 260 of 324) with no `DIFF-SILENT`, no crash, the other hard rules above, and `E` ≤ 1% for Gn; for M there is no MVP threshold (no file is inside `M1`) but the report must account for all 212 files. **Caveat:** the H part of the MVP gate rests on only 5 files, so it says little about real hand-written OEF; it is a smoke test, and the hand-written evaluation set E-O (Q2) is what measures real-world coverage.

---

## 15. Phased plan

| Phase | Content | Exit criteria |
|---|---|---|
| **P0 — Foundations** | decide Q7 (licence); add the schema fixtures and runner (done in v0.2, §13.1); take over `oef_validate.py` lexer as the shared parser (REQ-ARCH, §11.2); spec files `oef_spec.json`, `xml_block_catalog.json`; CLI skeleton, report writer, gate wrapper (REQ-ARCH-4). | AC-1, AC-2, AC-3 (fixtures), AC-13 |
| **P1 — MVP** | header/metadata (M-01…M-08), `\integer \real \text` with `randint`/`random`, arithmetic, `shuffle`/`randitem`/`item`/`items`, `\if`/`\for`/`\while`, `\statement` with text/`\var`/`\(…\)`/`\embed`, answer types numeric, case/text, formal family, radio, checkbox; placeholders, taint, report, deterministic ids, shape lint. | MVP gate of §14.2; AC-5…AC-8, AC-11, AC-12 |
| **P2 — Breadth** | lists and `lists_*` mapping, `\matrix` family (needs Q13), `\function` + `evalue/diff/simplify`, the six `wims()` subcommands, the forward-converter `pari/maxima` patterns, correspond/reorder/menu, HTML handling (`--html`), images and assets, idiom recognition (§6.6), trig behind `--trig-units`. | Gn: `C` ≥ 30% of bound; H and M `Q` thresholds of §14.2 |
| **P3 — Evaluation and feedback** | `\condition`/`\feedback` for the forward-emitted patterns, static steps (REQ-STEP-1), `\solution`/`\hint` mapping if Q10 is answered; RT-A, RT-B, RT-C complete; E-O if Q2 answered. | AC-9, AC-10 |
| **P4 — Optional** | simple flydraw primitives (M-53), `--llm-assist` stays out of scope, PyInstaller `.exe` (Q11), minimal web page. | owner decision |

Dependencies on answers: Q1 → REQ-OUT-5, REQ-TODO-4, AC-4; Q5 → fidelity upgrades (REQ-REP-7) and placeholder carrier; Q6 → trig; Q13 → P2 matrix work; Q2 → AC-10 extension.

---


## 16. Risks

| ID | Risk | Effect | Mitigation |
|---|---|---|---|
| R1 | Schema-valid output that the target platform cannot import (catch-all type pattern, `any-content` fields, §2.3) | false confidence | whitelist + catalogue + shape lint (REQ-SCH-1…4); no "importable" claim (REQ-SCH-6); real import test requested (Q5, SC-5) |
| R2 | Unknown target-platform grading and field semantics (`decimal` tolerance, `unique`/`multiple`, `mutation_shape`, `raw_options`) | wrong grading although the structure is right | `fidelite: non_verifiee` (REQ-REP-7); templates in data files (§8.3); Q5 |
| R3 | Ambiguous OEF expressions (list vs string, `\if` vs `\ifval`, `random(a,b)`) | silent wrong logic | exact `sp.c` rules (§7.2), taint (REQ-TODO-3), never best-effort trees (REQ-EXPR-6) |
| R4 | Raw HTML inside XML `text` blocks may not render | display defects (M-48) | `--html strict` → G-17; measured per element class; Q5 |
| R5 | GPL: WIMS is GPL, LaRuche GPL-3.0; code ported from `oef2wims` is a derivative work; the repository is AGPL-3.0 (Q7 closed) | legal | facts only in this spec (§1.3); decision before the first code commit (Q7, AC-13) |
| R6 | Corpus bias: generated files are machine-written, model templates are not exercises, only 121 files are hand-written | overstated quality | per-corpus targets (§14.2), evaluation sets E-H/E-M/E-O (§13.3), Q2 |
| R7 | Windows paths, encodings, long paths (`LongPathsEnabled=0`), ISO-8859-1 sources (80% upstream) | crashes, mojibake | REQ-IN-3, REQ-WIN-1…5 |
| R8 | v2 schemas and Schematron not supplied | requirements that cannot be checked | conditional requirements (REQ-OUT-5, REQ-TODO-4, AC-4); Q1 |
| R9 | WIMS version drift (4.31b verified; 4.27b mentioned by a reviewer) | different directives/limits | all facts carry source lines (Appendix A.3); Q3 |
| R10 | Placeholder carrier (`text` + comment icon) not confirmed in the target platform editor | invisible TODOs | switchable carrier (REQ-TODO-1); the `info` block also lists them; Q5 |
| R11 | Over-claiming `complet` | unsafe publication (cf. "reduced16", handoff line 9) | upper-bound FAIL rule (§14.2), AC-8, `--strict` |
| R12 | Gate wrapper pollutes the input folder (`.def/.log/.trace/.json` next to the input) | modified source tree | scratch-copy execution (REQ-ARCH-4, AC-11) |

---

## 17. Open questions and schema change requests

### 17.1 Open questions (Q1–Q13)

| ID | Question | Why it matters | Default until answered |
|---|---|---|---|
| Q1 | Can the v2 schemas `XML_program_v2.{dtd,xsd,rng,sch}` be supplied (in particular the Schematron rules R05 and the `TODO` domain-tag rule)? | REQ-OUT-5, REQ-TODO-4, REQ-VAL-2, AC-4 | v1 RNG/XSD only; own `aucune_question` flag |
| Q2 | Which of the owner's own hand-written OEF files can be used as evaluation set E-O (none is in the corpus)? | RT-B, AC-10 | the 121 upstream hand-written files |
| Q3 | Which WIMS version(s) must be supported? Everything here is verified against 4.31b sources; a reviewer mentioned 4.27b. | directive/limit tables (Appendix A.3), R9 | 4.31b |
| Q4 | Will the schema accept `source_format="oef"` (SC-1)? | REQ-SCH-5 | `ir` |
| Q5 | Can the target platform provide an importer or runtime test and documentation of: question fields (`mutation_shape`, `moreOptions`, `raw_options`, `answer`, `question`, `default_feedbacks`), grading semantics, raw HTML in `text`, comment icons on a `text` block and newlines in icon text? | REQ-SCH-6, REQ-REP-7, §8.3, REQ-TODO-1, M-48 | `non_verifiee`, modal templates, `--placeholder-carrier text` |
| Q6 | Does XML `math_trig` use degrees or radians? (the forward converter assumed degrees, `MAPPING.md:22`) | REQ-EXPR-4, G-21 | trig is a gap unless `--trig-units` is given |
| Q7 | Which licence for OEF2XML, given WIMS (GPL) and LaRuche (GPL-3.0)? May code be derived from `oef2wims`? | §1.3, R5, AC-13 | **Closed 2026-11-10: AGPL-3.0.** Compatible: WIMS `oef2wims` sources are GPL v2 *or later* (header of `src/OefMsg2wims/oef2wims.c`), so GPL-3.0 applies and GPLv3 §13 allows combination with AGPL-3.0; LaRuche GPL-3.0 likewise |
| Q8 | Default `max_attempts` (M-08)? | `info.max_attempts` | 1, reported as `info` |
| Q9 | Should `settings` timestamps/`template` be stamped (REQ-OUT-6)? | settings | omitted unless `--stamp` |
| Q10 | Mapping of `\solution`, `\hint`, `\help` (post-answer display in `feedbacks`?) | M-51, G-03 | placeholder |
| Q11 | Distribution: Python 3.12 + `lxml` or a single PyInstaller `.exe`? | §11.1, REQ-WIN-6 | **Closed 2026-11-10:** Python 3.12 + `lxml`; PyInstaller exe optional in P4 |
| Q12 | Languages `ca cn nl si`: extend the schema (SC-2) or drop? | G-04, G-20 | fall back to `--default-lang`, report |
| Q13 | Exemplars for the matrix/table blocks (`matrix{typeOf}`, `table_matrix`/`data_table` `LINE_n`) and for the `VALUE`/`FIND` roles of `lists_indexOf`. | M-19, M-21, G-10, phase 2 | placeholder (G-10) |

### 17.2 Schema change requests

These are requests to the schema owner; this project does not modify the schemas (§3.2). Each is linked to the question that motivates it.

| ID | Request | Motivation | Question |
|---|---|---|---|
| SC-1 | add `oef` to the `source_format` enumeration (RNG lines 19–22, XSD equivalent) | provenance of migrated programs; today `ir` is used | Q4 |
| SC-2 | add `ca cn nl si` to `lang/@code` (RNG lines 85–90) if those languages are wanted | OEF has `\language{ca}` (1 upstream file) and `\title_xx` | Q12 |
| SC-3 | make `<description>` optional in `lang-def` (RNG lines 93–94), or document that an empty element is the convention | upstream OEF has no `\description` | — (workaround: empty `<description/>`, fixtures of §13.1) |
| SC-4 | a documented, schema-level way to carry migration TODOs (e.g. an optional `todo` list in `settings`, or a documented comment-icon convention) | placeholders currently rely on comment icons (REQ-TODO-1) | Q5 |
| SC-5 | tighten the block-type enumeration (remove the catch-all pattern, RNG line 440 / XSD line 1158) and/or add Schematron shape rules per block type | schema validity currently says nothing about importability (R1) | Q1, Q5 |

---

## Appendix A — Corpus statistics, answer classes, WIMS command tables

### A.1 Corpus statistics (`oef_corpus_stats.py` → `corpus_stats.json`, `corpus_stats.md`, `per_file.csv`)

Groups: **H** = upstream hand-written (104 class + 17 module), **M** = upstream model templates, **U** = H + M, **Gn** = generated by the owner's `xml2oef`. The 5 own test files `e1`–`e5` are excluded. 1438 files in `corpus.map`, 1433 analysed, 0 parse errors.

| | H | M | U | Gn |
|---|---:|---:|---:|---:|
| files | 121 | 212 | 333 | 1100 |
| median bytes | 838 | 4291 | 3146 | 3798 |
| max bytes | 9258 | 22666 | 22666 | 132386 |
| directives per file, median | 12 | 42 | 31 | 48 |
| directives per file, p90 | 45 | 95 | 88 | 246 |
| directives per file, max | 88 | 208 | 208 | 738 |
| files over 1024 directives | 0 | 0 | 0 | 0 |
| not valid UTF-8 (ISO-8859) | 92 | 175 | 267 | 0 |
| CRLF files | 0 | 4 | 4 | 0 |
| files calling `wims()` | 35 | 195 | 230 | 430 |
| files calling `slib()` | 11 | 91 | 102 | 0 |
| files calling `pari()` | 11 | 10 | 21 | 89 |
| files calling `randint()` | 36 | 34 | 70 | 1026 |
| files calling `random()` | 21 | 0 | 21 | 256 |
| files calling `shuffle()` | 26 | 128 | 154 | 93 |
| files calling `draw()` | 25 | 12 | 37 | 0 |
| files with `\special` | 46 | 12 | 58 | n/a |
| files with `\embed` | 88 | 193 | 281 | 803 |

Scope bounds (`scope_bounds.py`, §14.2):

| | H | M | Gn |
|---|---:|---:|---:|
| files | 121 | 212 | 1100 |
| complet-eligible (upper bound) | 19 | 4 | 465 |
| ≥ 1 convertible question (upper bound) | 70 | 57 | 973 |
| no convertible question | 51 | 155 | 127 |
| files inside the phase-1 scope `M1` | 5 | 0 | 324 |

Most frequent directives (files containing them):

- **H**: `statement` 121, `title` 121, `answer` 109, `text` 75, `integer` 66, `author` 63, `email` 61, `precision` 52, `computeanswer` 52, `language` 49, `format` 48, `range` 41, `matrix` 39, `for` 17, `feedback` 15, `hint` 14
- **M**: `answer` 212, `author` 212, `text` 212, `statement` 212, `title` 212, `email` 212, `credits` 200, `integer` 181, `for` 128, `matrix` 117, `if` 113, `steps` 93, `latex` 52, `real` 47, `css` 44, `nextstep` 25
- **U**: `statement` 333, `title` 333, `answer` 321, `text` 287, `author` 275, `email` 273, `integer` 247, `credits` 213, `matrix` 156, `for` 145, `if` 126, `steps` 101, `precision` 66, `real` 60, `computeanswer` 57, `language` 54
- **Gn**: `language` 1100, `title` 1100, `statement` 1100, `author` 1089, `integer` 1061, `text` 1031, `answer` 973, `real` 930, `ifval` 738, `description` 595, `if` 531, `feedback` 505, `while` 484, `for` 417, `matrix` 144, `condition` 90

Most frequent `wims()` subcommands (calls): 
- **H**: `replace` 43, `trim` 34, `values` 29, `char` 27, `append` 23, `rowcnt` 18, `makelist` 12, `charcnt` 11, `sort` 8, `item` 6, `listintersect` 6, `itemcnt` 6
- **M**: `append` 246, `replace` 231, `makelist` 220, `embraced` 211, `word` 158, `nonempty` 142, `items2words` 104, `select` 49, `singlespace` 47, `text` 47, `sort` 46, `values` 42
- **U**: `replace` 274, `append` 269, `makelist` 232, `embraced` 216, `word` 158, `nonempty` 143, `items2words` 104, `values` 71, `sort` 54, `charcnt` 50, `select` 50, `singlespace` 47
- **Gn**: `nonempty` 2172, `char` 1246, `charcnt` 1030, `replace` 584, `sort` 245, `makelist` 232, `lowercase` 34, `uppercase` 7

`slib()` modules (calls): **H**: `draw/convpixel` 4, `oef/insfilename` 4, `function/bounds` 2, `data/random` 2, `text/sigunits` 1, `text/matrixhtml` 1; **M**: `text/cutchoice2` 42, `draw/convpixel` 15, `oef/env` 12, `text/markgroup` 10, `utilities/nopaste` 10, `lang/swac` 10; **U**: `text/cutchoice2` 42, `draw/convpixel` 19, `oef/env` 12, `text/markgroup` 10, `utilities/nopaste` 10, `lang/swac` 10

Languages declared: **H**: `fr` 36, `it` 10; **U**: `fr` 38, `it` 10, `es` 1, `ca` 1, `en` 1; **Gn**: `fr` 1032, `en` 48, `de` 13, `it` 6, `ar` 1

Answer types by files (U): `DYNAMIC` 74, `dragfill` 31, `clickfill` 25, `checkbox` 20, `case` 18, `mark` 14, `correspond` 14, `number` 12, `menu` 11, `numeric` 11, `puzzle` 10, `default` 8, `radio` 8, `vector` 7, `(none:` 6, `jsxgraphcurve` 6, `multipleclick` 6, `function` 6, `formal` 6, `matrix` 5. Generated: `numeric` 581, `radio` 301, `correspond` 51, `formal` 50, `case` 28, `reorder` 23, `checkbox` 15.

### A.2 Answer-type classes (structural, as used by the statistics)

`D` structurally direct, `A` approximate, `G` gap. **In the report every question mapping is at best `A` for fidelity until Q5 (§8.2, REQ-REP-7).** The canonical `replytype` is what `oef2wims` writes into the `.def` (`process.c:173–221`).

| `type=` | canonical replytype | class | | `type=` | canonical replytype | class |
|---|---|---|---|---|---|---|
| `algexp` | `algexp` | A | | `litexp` | `litexp` | A |
| `aset` | `aset` | G | | `mark` | `mark` | G |
| `atext` | `atext` | A | | `matrix` | `matrix` | G |
| `case` | `case` | A | | `menu` | `menu` | A |
| `checkbox` | `checkbox` | D | | `nocase` | `nocase` | A |
| `chemeq` | `chemeq` | G | | `number` | `numeric` | D |
| `chset` | `chset` | A | | `numeric` | `numeric` | D |
| `click` | `click` | G | | `numexp` | `numexp` | A |
| `clickfill` | `clickfill` | G | | `radio` | `radio` | D |
| `code` | `code` | G | | `range` | `range` | A |
| `compose` | `compose` | G | | `ranges` | `range` | A |
| `coord` | `coord` | G | | `raw` | `raw` | A |
| `coordinates` | `coord` | G | | `reorder` | `reorder` | D |
| `corresp` | `correspond` | D | | `select` | `menu` | A |
| `correspond` | `correspond` | D | | `set` | `set` | G |
| `default` | `default` | A | | `sigunits` | `sigunits` | G |
| `dragfill` | `dragfill` | G | | `symtext` | `symtext` | A |
| `equation` | `equation` | A | | `text` | `case` | A |
| `expalg` | `algexp` | A | | `textcomp` | `textcomp` | G |
| `formal` | `formal` | A | | `unit` | `units` | G |
| `fset` | `fset` | G | | `units` | `units` | G |
| `function` | `function` | A | | `vector` | `vector` | G |
| `imgcomp` | `imgcomp` | G | | `wlist` | `wlist` | G |
| `javacurve` | `javacurve` | G | | `wordcomp` | `textcomp` | G |
| `link` | `click` | G | | | | |

### A.3 WIMS 4.31b command tables with source references

Source: `/workspace/oefc/src431/src/OefMsg2wims/` (WIMS 4.31b, Debian `wims_4.31b+dfsg1.orig.tar.gz`, sha256 `b8091a9a…c13fb9`, per `LISEZMOI.txt` of the repo). Line numbers are those of that tree. Only identifiers and behaviour are recorded (§1.3).

#### A.3.1 Directives (55; table `oef2wims.c:61–115`)

| directive | `oef2wims.c` line | max params | processor | family | spec |
|---|---:|---:|---|---|---|
| `\answer` | 61 | 5 | `p_answer` | answer | §8 |
| `\author` | 62 | 1 | `p_header` | header (keyword form) | M-04 |
| `\choice` | 63 | 5 | `p_choice` | choice | §8 |
| `\complex` | 64 | 2 | `p_complex` | definition/control | G (not mapped) |
| `\computeanswer` | 65 | 1 | `p_computeanswer` | header | G-02 |
| `\condition` | 66 | 4 | `p_condition` | condition | G-15 |
| `\conditions` | 67 | 1 | `p_conditions` | conditions | G-15 |
| `\credits` | 68 | 2 | `p_credits` | definition/control | G-02 |
| `\css` | 69 | 1 | `p_css` | header | G-02 |
| `\description` | 70 | 1 | `p_description` | header | M-05 |
| `\else` | 71 | 0 | `p_else` | definition/control | M-28 |
| `\email` | 72 | 1 | `p_header` | header (keyword form) | G-01 |
| `\endif` | 73 | 0 | `p_endif` | definition/control | M-28 |
| `\endwhile` | 74 | 0 | `p_endwhile` | definition/control | M-29 |
| `\feedback` | 75 | 2 | `p_feedback` | feedback | §8.5 |
| `\for` | 76 | 1 | `p_for` | definition/control | M-29 |
| `\format` | 77 | 1 | `empty` | format | G-02/G-16 |
| `\function` | 78 | 2 | `p_func` | definition/control | M-22 |
| `\help` | 79 | 1 | `p_help` | help | G-03 |
| `\hint` | 80 | 1 | `p_hint` | hint | G-03 |
| `\if` | 81 | 1 | `p_if` | definition/control | M-28 |
| `\ifval` | 82 | 1 | `p_ifval` | definition/control | M-28 |
| `\int` | 83 | 2 | `p_int` | definition/control | M-10/12 |
| `\integer` | 84 | 2 | `p_int` | definition/control | M-10/12 |
| `\keywords` | 85 | 1 | `p_header` | header (keyword form) | M-06 |
| `\language` | 86 | 1 | `p_language` | header | M-02 |
| `\latex` | 87 | 1 | `p_latex` | TeX version | G-16 |
| `\matrix` | 88 | 2 | `p_matrix` | definition/control | M-21/G-10 |
| `\mdef` | 89 | 2 | `p_mdef` | definition/control | G-14 |
| `\next` | 90 | 0 | `p_next` | definition/control | M-29 |
| `\nextstep` | 91 | 1 | `p_nextstep` | steps | G-08/§9 |
| `\observation` | 92 | 1 | `p_observation` | header | G-02 |
| `\parameter` | 93 | 2 | `p_parm` | definition/control | G (not mapped) |
| `\plot` | 94 | 3 | `p_plot` | plot | G-09 |
| `\precision` | 95 | 1 | `p_precision` | header | G-02 |
| `\range` | 96 | 1 | `p_range` | header | G-02 |
| `\rational` | 97 | 2 | `p_rational` | definition/control | M-12 |
| `\real` | 98 | 2 | `p_real` | definition/control | M-11/12 |
| `\reply` | 99 | 5 | `p_answer` | answer | §8 |
| `\solution` | 100 | 1 | `p_solution` | solution | G-03 |
| `\statement` | 101 | 1 | `p_statement` | statement | M-40 |
| `\steps` | 102 | 1 | `p_steps` | steps | G-08/§9 |
| `\text` | 103 | 2 | `p_text` | definition/control | M-13/14 |
| `\title` | 104 | 1 | `empty` | title | M-01 |
| `\title_ca` | 105 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\title_cn` | 106 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\title_en` | 107 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\title_es` | 108 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\title_fr` | 109 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\title_it` | 110 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\title_nl` | 111 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\title_si` | 112 | 1 | `p_header` | title in another language | M-03/G-20 |
| `\variable` | 113 | 2 | `p_parm` | definition/control | G (not mapped) |
| `\while` | 114 | 1 | `p_while` | definition/control | M-29 |
| `\wims` | 115 | 1 | `p_wims` | raw wims | G (raw wims code) |

#### A.3.2 Answer types (49; table `process.c:173–221`)

See A.2: every row there is one entry of the table (`type=` value, canonical `replytype`). Unknown values are passed through (`process.c:~250`). `p_answer` starts at `process.c:227`, `p_choice` at `process.c:354`.

#### A.3.3 Special functions (40; table `sp.c:306–346`)

| function | `sp.c` table line | implementation line | spec |
|---|---:|---:|---|
| `asis` | 307 | 23 | text (verbatim) |
| `canvasdraw` | 308 | 167 | G-09 |
| `column` | 309 | 239 | P (M-21) |
| `deriv` | 310 | 64 | M-24 |
| `derivative` | 311 | 64 | M-24 |
| `det` | 312 | 73 | G-11 |
| `determinant` | 313 | 73 | G-11 |
| `diff` | 314 | 64 | M-24 |
| `draw` | 315 | 147 | G-09 |
| `drawtikz` | 316 | 157 | G-09 |
| `evaluate` | 317 | 28 | M-23 |
| `evalue` | 318 | 28 | M-23 |
| `htmlmath` | 319 | 95 | text |
| `int` | 320 | 82 | G-11 |
| `integral` | 321 | 82 | G-11 |
| `integrate` | 322 | 82 | G-11 |
| `item` | 323 | 217 | M-17 |
| `items` | 324 | 228 | M-18 |
| `mathexp_cut` | 325 | 288 | G-11 |
| `maxima` | 326 | 111 | M-26 / G-11 |
| `pari` | 327 | 123 | M-27 / G-11 |
| `pickone` | 328 | 212 | §7.2 |
| `position` | 329 | 182 | M-19 |
| `positionof` | 330 | 182 | M-19 |
| `randint` | 331 | 212 | M-10 (§7.2) |
| `randitem` | 332 | 233 | M-16 |
| `random` | 333 | 192 | M-11 (§7.2) |
| `randomitem` | 334 | 233 | M-16 |
| `randomrow` | 335 | 279 | P (M-21) |
| `randrow` | 336 | 279 | P (M-21) |
| `row` | 337 | 253 | P (M-21) |
| `rows` | 338 | 273 | P (M-21) |
| `shuffle` | 339 | 177 | M-15 |
| `simplify` | 340 | 129 | M-25 |
| `slib` | 341 | 137 | G-13 |
| `solve` | 342 | 53 | G-11 |
| `teximg` | 343 | 100 | G-09 |
| `texmath` | 344 | 106 | text |
| `wims` | 345 | 297 | §7.3 (6 subcommands) / G-12 |
| `yacas` | 346 | 117 | G-11 |

Notes: `random`/`randint` semantics `sp.c:192–212`; item functions `sp.c:217–233`; `rows`/`randrow` `sp.c:273–279`; context-dependent rewriting `parmprep` `sp.c:351–380`. Trigonometric functions are **not** in this table: they belong to the WIMS expression evaluator, not to `oef2wims`; their target-platform unit is Q6.

#### A.3.4 Limits, errors and silent behaviours

| Behaviour | Where | Treatment in this spec |
|---|---|---|
| `MAX_TITLEN` 80: `\title` silently truncated to 80 bytes | `oef2wims.c:20,325` | `info` detail (REQ-IN-5) |
| `MAX_PARM` 10, `MAX_PARAM` 1024 | `oef2wims.c:22–23` | not enforced by the tool |
| `MAX_DEFINE` 1024: scan stops after 1024 directives, rest silently ignored | `oef2wims.c:24,171` | **warning** `LIMIT-1024` (REQ-IN-5) |
| `MAX_FLEN` 199999: file ≥ 199999 bytes → `Source file bad or too long.` | `oef2wims.c:25,429`; `getinp` `143–165` | **error → echec** (REQ-IN-5) |
| empty file → `Empty source file.` | `oef2wims.c:430` | **error → echec** |
| unbalanced `() [] {}` → `Unmatched parentheses` | `oef2wims.c:431`; `oeflines.c:216` | error → echec |
| `MAX_PROMPTLEN` 40: `\answer` prompt ≥ 40 → `Answer prompt too long`; `\choice` prompt silently cut | `oef2wims.h:13`; `process.c:293,396` | error for `\answer`; `info` for `\choice` |
| no `\statement` → `No statement defined.`; second `\statement` → `Multiple definition of statement.`; second `\steps` → `Multiple definition of steps.` | `oef2wims.c:321,282,235` | errors → echec |
| unknown top-level `\name{…}` skipped silently | `oef2wims.c:207–209` | warning |
| CR and bytes 0–6 replaced by spaces | `oef2wims.c:143–165` | same in the parser (REQ-IN-4) |
| `-debug` path: `oef_debug()` is defined but never called by `main` | `oef2wims.c:127` | not relied upon |
| answer-time substitutions `\reply \result \choice \step \sc_reply \sc_choice \reply_` | `oeflines.c:111–138` | §7.1, M-50 |
| predefined parameters `imagedir`, `confparm1…4` | `oef2wims.c:437–442` | REQ-IN-6 |
| `$` → `&#36;` in `subst()` | `oeflines.c:65–` | §7.5 |

#### A.3.5 Commands handled at text level (`outexec.c`)

`\exit` (`outexec.c:171`), `\for` (176), `\if` (183), `\ifval` (190), `\img` (197), `\audio` (198), `\slib` (199), `\embed` (200), `\special` (201), `\draw` (202), `\drawtikz` (203), `\canvasdraw` (204). They are recognised **inside text** (statement, hint, …), not only as top-level directives, so the lexer must scan text parameters for them.


## Appendix B — XML block catalogue and reverse idioms

### B.1 Block catalogue (`xml_block_catalog.py` → `xml_block_catalog.json`)

Built from the 1116 programs of `/workspace/xml_etudes`: **169 distinct block types, all inside the 190-value enum**; 190 enum values, of which the 21 never observed are forbidden (REQ-SCH-3). `source_format`: {'json': 1019, 'xml': 97}. The JSON file also records, per type, the field names, input names, `extraState` children and the observed values of each field; the emitter and the shape lint read it (REQ-SCH-2, REQ-VAL-3).

"Used" = the type appears in a mapping row or requirement of this document.

| block type | blocks | programs | top-level | used |
|---|---:|---:|---:|---|
| `variables_get` | 89143 | 1102 | 51 | yes |
| `text` | 49204 | 1100 | 187 | yes |
| `math_number` | 35167 | 1002 | 91 | yes |
| `math_arithmetic` | 33963 | 976 | 36 | yes |
| `variables_set` | 22987 | 1101 | 12 | yes |
| `logic_compare` | 15527 | 888 | 11 | yes |
| `random_number` | 9656 | 1031 | 6 | yes |
| `display_element` | 8276 | 1055 | 13 | yes |
| `logic_ternary` | 7773 | 411 | 7 | yes |
| `point` | 7298 | 344 | 33 | yes |
| `list_short_get` | 7119 | 332 | 3 | yes |
| `lists_create_with` | 5761 | 867 | 13 | yes |
| `controls_if` | 5055 | 852 | 6 | yes |
| `richtext_create_with` | 4720 | 786 | 5 | yes |
| `set_alignment` | 4714 | 790 | 4 | yes |
| `draw_in_board` | 4399 | 364 | 4 | yes |
| `text_join` | 4172 | 409 | 3 | yes |
| `latex` | 4108 | 334 | 0 | yes |
| `logic_operation` | 3777 | 470 | 10 | yes |
| `math_number_property` | 3763 | 347 | 0 | yes |
| `set_colour` | 3272 | 442 | 15 | yes |
| `coordinate` | 3220 | 135 | 4 |  |
| `latex_paragraph_create_with` | 2813 | 483 | 0 | yes |
| `round_decimal` | 2354 | 310 | 0 |  |
| `lists_getIndex` | 1934 | 352 | 4 | yes |
| `line` | 1859 | 256 | 0 | yes |
| `question_open` | 1777 | 676 | 0 | yes |
| `set_size` | 1701 | 321 | 8 | yes |
| `procedures_callnoreturn` | 1638 | 532 | 0 |  |
| `matrix_short_get` | 1535 | 109 | 3 | yes |
| `math_single` | 1454 | 251 | 5 | yes |
| `math_round` | 1452 | 182 | 5 | yes |
| `controls_whileUntil` | 1430 | 464 | 0 | yes |
| `procedures_defnoreturn` | 1276 | 533 | 1276 | yes |
| `controls_for` | 1250 | 294 | 1 | yes |
| `info` | 1115 | 1115 | 1115 | yes |
| `special_character` | 1108 | 301 | 0 | yes |
| `text_multiline` | 1064 | 122 | 1 | yes |
| `is_solution_found` | 946 | 526 | 0 | yes |
| `logic_negate` | 939 | 387 | 1 | yes |
| `matrix_short_set` | 844 | 60 | 0 |  |
| `polygon` | 822 | 132 | 1 | yes |
| `current_attempt` | 787 | 327 | 0 | yes |
| `lists_setIndex` | 769 | 187 | 0 | yes |
| `math_trig` | 766 | 59 | 0 | yes |
| `board_geometric` | 739 | 364 | 0 | yes |
| `expression` | 720 | 105 | 1 | yes |
| `procedures_callreturn` | 685 | 132 | 3 |  |
| `board_text` | 678 | 146 | 0 |  |
| `lists_length` | 659 | 103 | 0 | yes |
| `max_attempts` | 588 | 316 | 0 | yes |
| `split_number` | 571 | 60 | 0 | yes |
| `fraction` | 555 | 146 | 3 | yes |
| `set_attribute` | 506 | 64 | 1 |  |
| `random_message` | 462 | 166 | 2 | yes |
| `markdown` | 448 | 145 | 1 | yes |
| `data_table` | 430 | 138 | 0 | yes |
| `logic_boolean` | 420 | 92 | 0 | yes |
| `evaluate` | 407 | 55 | 0 | yes |
| `question_multiple_choices` | 403 | 274 | 0 | yes |
| `euclidean_distance` | 375 | 16 | 0 |  |
| `lists_sort` | 369 | 81 | 0 | yes |
| `lists_indexOf` | 363 | 45 | 2 | yes |
| `statement` | 353 | 290 | 0 | yes |
| `versions` | 344 | 344 | 0 | yes |
| `math_modulo` | 322 | 109 | 0 | yes |
| `integer_decimal_part` | 303 | 51 | 2 |  |
| `simplify_fraction` | 298 | 51 | 0 |  |
| `context_question` | 241 | 157 | 0 | yes |
| `procedures_defreturn` | 240 | 135 | 240 | yes |
| `table_column` | 212 | 42 | 0 |  |
| `circle` | 195 | 68 | 0 | yes |
| `binomial_1` | 192 | 8 | 0 |  |
| `math_random_int` | 191 | 46 | 0 | yes |
| `poisson_1` | 190 | 8 | 0 |  |
| `polynom_with_coefficients` | 188 | 58 | 0 | yes |
| `delete_element_from_list` | 184 | 86 | 0 |  |
| `fraction_numerator_denominator` | 183 | 28 | 0 |  |
| `lists_split` | 174 | 61 | 0 |  |
| `feedback_global` | 171 | 156 | 8 | yes |
| `figure_area` | 158 | 20 | 1 |  |
| `shuffle_list` | 157 | 98 | 0 | yes |
| `math_on_list` | 152 | 59 | 0 | yes |
| `controls_repeat_ext` | 150 | 83 | 0 | yes |
| `graph_of_function` | 143 | 64 | 0 | yes |
| `coefficients` | 141 | 24 | 0 | yes |
| `question_figure` | 137 | 124 | 3 | yes |
| `gcd_lcm` | 133 | 48 | 0 | yes |
| `feedback_message_type` | 127 | 127 | 0 |  |
| `list_short_set` | 111 | 44 | 0 |  |
| `random_list` | 110 | 69 | 0 |  |
| `selected_verb` | 100 | 10 | 0 |  |
| `integer_part` | 93 | 18 | 0 |  |
| `question_true_false` | 84 | 46 | 1 | yes |
| `sector` | 84 | 15 | 0 |  |
| `matrix_3_parameters` | 84 | 58 | 0 |  |
| `conjugate_verb` | 79 | 9 | 0 |  |
| `text_indexOf` | 72 | 31 | 0 |  |
| `image` | 67 | 15 | 0 | yes |
| `table_matrix` | 61 | 21 | 0 | yes |
| `text_changeCase` | 60 | 28 | 0 | yes |
| `matrix` | 58 | 14 | 0 | yes |
| `derivative` | 58 | 20 | 0 | yes |
| `question_associate` | 52 | 52 | 0 | yes |
| `geometric_1` | 52 | 9 | 0 |  |
| `video` | 49 | 23 | 0 | yes |
| `math_change` | 47 | 24 | 0 |  |
| `set_colour_random` | 46 | 12 | 2 |  |
| `expand_algebrite` | 45 | 12 | 0 | yes |
| `erase_in_board` | 44 | 18 | 0 |  |
| `delete_duplicates` | 43 | 41 | 0 |  |
| `math_constant` | 41 | 10 | 0 | yes |
| `degree` | 38 | 15 | 0 | yes |
| `text_replace` | 38 | 11 | 0 | yes |
| `text_length` | 37 | 21 | 1 | yes |
| `uniform_4` | 37 | 7 | 0 |  |
| `expo_4` | 37 | 7 | 0 |  |
| `normal_4` | 37 | 7 | 0 |  |
| `count_same_element_list` | 36 | 17 | 0 |  |
| `lists_reverse` | 36 | 10 | 0 |  |
| `lists_repeat` | 34 | 14 | 0 |  |
| `set_analytic` | 33 | 10 | 0 |  |
| `rectangle` | 30 | 15 | 0 |  |
| `text_charAt` | 28 | 20 | 0 | yes |
| `dictionary` | 27 | 11 | 0 |  |
| `random_polynom` | 25 | 24 | 0 |  |
| `euclidean_distance_twopoints` | 25 | 6 | 0 |  |
| `question_reorder` | 23 | 23 | 0 | yes |
| `random_verb` | 21 | 11 | 0 |  |
| `clean_activity` | 18 | 4 | 0 |  |
| `text_getSubstring` | 18 | 9 | 0 |  |
| `controls_forEach` | 18 | 3 | 0 | yes |
| `erase_all_board` | 17 | 9 | 0 |  |
| `verb_getAttribute` | 17 | 10 | 0 |  |
| `lists_getSublist` | 15 | 4 | 0 |  |
| `matrix_determinant` | 12 | 9 | 0 |  |
| `binomial_3` | 12 | 2 | 0 |  |
| `text_append` | 9 | 6 | 0 |  |
| `random_polygon` | 9 | 8 | 0 |  |
| `geometric_2` | 8 | 2 | 0 |  |
| `poisson_2` | 8 | 2 | 0 |  |
| `uniform_1` | 8 | 2 | 0 |  |
| `expo_1` | 8 | 2 | 0 |  |
| `normal_1` | 8 | 2 | 0 |  |
| `lists_isEmpty` | 8 | 2 | 0 |  |
| `figure_perimeter` | 7 | 2 | 0 |  |
| `controls_flow_statements` | 6 | 5 | 0 |  |
| `convert_into_unit` | 6 | 4 | 0 |  |
| `unit` | 6 | 4 | 0 |  |
| `set_grade` | 6 | 4 | 0 |  |
| `geometric_3` | 6 | 2 | 0 |  |
| `poisson_3` | 6 | 2 | 0 |  |
| `split_into_words_letters` | 6 | 5 | 0 |  |
| `simplify_algebrite` | 5 | 3 | 0 | yes |
| `matrix_multiplication` | 5 | 5 | 0 |  |
| `uniform_2` | 5 | 3 | 0 |  |
| `expo_2` | 5 | 3 | 0 |  |
| `normal_2` | 5 | 3 | 0 |  |
| `figure_rotate` | 3 | 3 | 0 |  |
| `decimal_part` | 2 | 2 | 0 |  |
| `binomial_2` | 2 | 2 | 0 |  |
| `area_under_function_interval` | 2 | 1 | 0 |  |
| `sound` | 2 | 2 | 0 | yes |
| `figure_translate` | 2 | 2 | 0 |  |
| `adjective_getAttribute` | 1 | 1 | 0 |  |
| `random_adjective` | 1 | 1 | 0 |  |
| `selected_name` | 1 | 1 | 0 |  |
| `determinantDefInfDemons_getAttribute` | 1 | 1 | 0 |  |
| `selected_determinantDefInfDemons` | 1 | 1 | 0 |  |

Never observed (not to be emitted): `QUESTION`, `adjectives`, `arrow`, `conjugations`, `decimal`, `definis`, `denominator`, `determinants`, `dotted`, `integer`, `integerPositive`, `kids`, `letters`, `multiple`, `names`, `numerator`, `segment`, `string`, `table`, `unique`, `verbs`.

### B.2 Reverse idioms of the forward converter (`xml2oef/MAPPING.md`)

Each row is a rule of the forward converter and what the reverse tool does with the OEF shape it produces. Recognition is switchable (`--idioms`, REQ-IDIOM-3) and limited to the exact shapes listed (REQ-IDIOM-2). "MAPPING.md:n" = line in `/workspace/xml2oef/MAPPING.md`.

| Forward rule (the target platform → OEF) | OEF shape produced | Reverse treatment | Fid. | MAPPING.md |
|---|---|---|---|---:|
| title cut to 78 bytes | `\title{…}` | `<name>`, `<title>`, `default_title`; the cut is not recoverable (reported `info`) | A | 8 |
| `default_lang` → language; description; author | `\language \description \author` | M-02, M-05, M-04 | E | 9–11 |
| `max_attempts`, `default_feedback` | `%%` comment only | not recoverable; `--max-attempts`, REQ-OUT-6 / M-08 | A | 12 |
| variable names made ASCII (`réponse 1` → `reponse_1`), suffix `_v` for reserved names, `_2` on collision | renamed identifiers | original names are lost; OEF names kept verbatim (REQ-OUT-7) | A | 17 |
| sub-expression → temporary `\x2oN` | `\text/\integer/\real{x2oN=…}` used once | a temporary defined once and read once is inlined back into the expression; otherwise kept as a variable `x2oN` | A | 19 |
| `random_number`, `math_random_int` | `randint(a..b)`, `random(a..b)` | M-10, M-11 | E / A | 20 |
| arithmetic, `math_single`, `math_round`, `round_decimal`, `math_modulo`, `math_constant` | `+ - * / ^`, `abs sqrt ln log10 exp`, `rint ceil floor`, `rint(x*10^d)/10^d`, `%`, `pi e` | REQ-EXPR-3; the `rint(x*10^d)/10^d` shape → `round_decimal` (A) | E / A | 21 |
| `math_trig` (hypothesis: degrees) | `sin(x*pi/180)` | **G-21** unless `--trig-units` is given: with `deg`, the `*pi/180` factor is stripped and `math_trig` gets `x`; with `rad`, the expression is kept as is; never converted silently (REQ-EXPR-4, Q6) | G / A | 22 |
| `integer_part`, `decimal_part` | `floor(x)`, `x-floor(x)` | left as arithmetic (A); not folded back | A | 23 |
| list blocks | `\L[i]`, `randitem()`, `items()`, `wims(replace item number …)`, `wims(sort [numeric] items …)`, `position()`, `shuffle()`, `\for` loops | M-14…M-20, §7.3 | E / A | 24 |
| `data_table`, `table_matrix`, `matrix_short_get` | `\matrix{…}`, `\M[i;j]` | P (M-21, Q13) | P | 25 |
| `logic_ternary` | `\if{c}{\text{t=A}}{\text{t=B}}` | `logic_ternary` when the two branches only assign the same variable (A); else `controls_if` | A | 26 |
| boolean stored as integer 0/1 | `\integer{b=0 or 1}` | not recoverable: stays an integer (`info`) | A | 27 |
| `fraction`, `simplify_fraction`, numerator/denominator | text `a/b`, `pari(…)`, `pari(numerator(…))` | literal `a/b` → `fraction` (M-12), `pari` per M-27/G-11 | A | 28 |
| polynomials, derivative, evaluate, expand, simplify | `pari(Pol([…]))`, `pari(Vec(…))`, `pari(poldegree())`, `diff()`, `evalue()`, `maxima(expand())`, `simplify()` | M-23…M-27 | E / A | 29 |
| text blocks | concatenation, `wims(replace internal …)`, `wims(lowercase/uppercase …)`, `wims(charcnt …)`, `wims(char k of …)` | §7.3 (the six mapped subcommands) | E | 30 |
| `logic_compare`; equality numeric → `\ifval`, text → `\if`; mixed → precomputed 0/1 | `== != < <= > >=` | M-30 (`A` on mixed) | E / A | 35 |
| `logic_operation`, `logic_negate` (De Morgan, inverted operators) | `and or`, inverted comparisons | `logic_negate` is not reconstructed (A) | A | 36 |
| `math_number_property` | `> 0`, `< 0`, `%2`, `floor`, `pari(isprime())` | `isprime` pattern only (M-27); others stay arithmetic | A | 37 |
| `controls_if`, `controls_whileUntil`, `controls_for`, `controls_repeat_ext`, `controls_forEach` | nested `\if`/`\ifval`, `\while`, `\for{i=a to b}`, `\for{x in \L}` | M-28, M-29; UNTIL is recorded as a negated WHILE (`info`) | E / A | 38–40 |
| procedures unrolled at each call | repeated code | procedures are **not** recreated (`info`) | A | 41 |
| `versions` | `\x2oversion` = DEFAULT or random draw, one `\ifval` per version | no equivalent in OEF semantics; the variable stays an ordinary integer; `versions` is not rebuilt (`info`) | A | 42 |
| `display_element`, `statement` → `\statement` (HTML) | `<br>`, `\(…\)`, `<b>/<i>`, `<div style>`, `<span style>`, `<img>`, accumulated `\x2oN` variable inside the statement | M-40…M-48; the accumulator variable is inlined when used once in the statement | A | 45 |
| `question_open` integer/decimal/fraction; string/expression | `\answer{Réponse n}{\sol}{type=numeric}`; `type=case`; `type=formal` | §8.2 | A† | 50–51 |
| answer predicate (`callbackSolution`) | unset variable `\x2orepN` + `\condition{Réponse n}{…}` | §8.5 (phase 3); else G-15 | A / G | 52 |
| `question_multiple_choices` | `\answer{}{1,…;good,bad}{type=radio or checkbox}{option=shuffle}` | §8.2 | A† | 53 |
| `question_true_false` | `\answer{}{1 or 2;Vrai,Faux}{type=radio}` | a radio with exactly the pair Vrai/Faux → `question_true_false` (A, §8.2) | A | 54 |
| `question_reorder`, `question_associate` | `type=reorder`, `type=correspond` (`\l1;\l2`) | §8.2 | A† | 55 |
| question text | statement text with `\embed{replyN}` | M-49, §8.3 | A | 56 |
| feedback blocks, `is_solution_found`, answer references | `\feedback{cond}{msg}`, `\sc_replyN == 1`, `\replyN`; computations placed after `\statement` | §8.5 (phase 3); post-definitions kept with the `post` phase tag (§7.1) | A | 58–59 |
| delimiter balancing, one `\statement`, prompts < 40, item commas `&#44;` | entities `&#40; &#41; &#91; &#93; &#123; &#125; &#44;` | kept verbatim in text; `&#44;` is decoded only when splitting a list into items | E | 62–63 |
| size limits checked before writing | file < 199 999 bytes, ≤ 1024 directives | the same limits are reported by REQ-IN-5 | — | 64 |
| blocks not translated | `%% x2o NON TRADUIT [type, ligne XML n] : reason` | **G-22** (REQ-IDIOM-1) | G | 3, 66 |
| approximations | `%% x2o approximation …` | `approximation` detail | A | 3 |


## Appendix C — Artefacts, reproduction, evidence, corrections

### C.1 Artefacts (all under `/workspace/oef2xml/` unless stated)

| Artefact | Purpose | Reproduce |
|---|---|---|
| `CAHIER_DES_CHARGES_OEF2XML.md` | this document (v0.2) | — |
| `oef_corpus_stats.py`, `corpus_stats.json`, `corpus_stats.md`, `per_file.csv` | corpus statistics (A.1), tier `M1_mvp_scope` | `python3 oef_corpus_stats.py [--corpus DIR --map FILE --out DIR]` |
| `scope_bounds.py`, `scope_bounds.json` | upper bounds of §14.2 | `python3 scope_bounds.py [--corpus DIR --map FILE --out FILE]` |
| `xml_block_catalog.py`, `xml_block_catalog.json` | block catalogue (B.1) | `python3 xml_block_catalog.py --xml /workspace/xml_etudes --rng <rng> --out …` |
| `check_refs.py` | cross-reference check (C.4) | `python3 check_refs.py` |
| `/workspace/OEF2XML_repo/validation/xml/tests/` | schema fixtures and runner (§13.1) | `python3 run_schema_tests.py -v` |

Inputs: corpus `/workspace/oefc/corpus` + `corpus.map` (1438 files: 1100 generated, 104 class, 17 module, 212 model, 5 own tests excluded); XML programs `/workspace/xml_etudes` (1116); WIMS 4.31b sources `/workspace/oefc/src431/src/`; compiler wrappers `/workspace/oefc/e2pkg/E2_build/sources/`; forward converter `/workspace/xml2oef/`; attachments (RNG `e744b791…xml`, XSD `b138e2db…xml`, handoff `44e04b8a…md`) under `/home/box/agent-data/agents/9762ce64-b543-44f1-93c3-9f8b55f8ceb1/attachments/` (the path quoted in the original brief did not exist).

### C.2 Evidence index

| Claim | Evidence |
|---|---|
| enum of 190 values + catch-all pattern | RNG line 440; XSD union lines 205–1161, pattern line 1158 |
| `source_format` ∈ json, yaml, ir, xml | RNG lines 19–22 |
| `lang/@code` ∈ fr en es it de ar | RNG lines 85–90 |
| `<title>` and `<description>` both required in `<lang>` | RNG lines 93–94; fixtures `invalid/lang_missing_description.xml`, `valid/minimal_info_chain.xml` |
| comment icon format | `xml_etudes/1008.xml:40-42`, `3368.xml:543-545`; 2085 icons, attributes `text pinned height width` |
| 187 top-level `text` blocks, 13 top-level `display_element` | `xml_block_catalog.json`, `top_level_blocks` |
| 55 directives / 49 answer types / 40 special functions | `oef2wims.c:61–115`, `process.c:173–221`, `sp.c:306–346` (A.3) |
| MAX_DEFINE / MAX_FLEN / MAX_TITLEN / MAX_PROMPTLEN | `oef2wims.c:20–25,171,325,429–431`; `oef2wims.h:13`; `process.c:293,396` |
| `random`/`randint` semantics | `sp.c:192–212`, `parmprep` `sp.c:351–380` |
| `\choice` has no `type=` | `process.c:354–` (only `option`, `weight`) |
| answer-time substitutions | `oeflines.c:111–138` |
| `--json` writes `<name>.json` next to the log, not stdout | `oef2wims_v2.c:195–196, 303, 350, 365–367, 393`; `oef2wims_log.c` has no `--json` |
| repository content, no LICENSE | `gh api repos/io-e/OEF2XML` (public) and `git/trees/main?recursive=1`, 2026-11-09 |
| R05 / TODO tag only described by the handoff | handoff lines 40 and 52 |

### C.3 Corrections to v0.1 (§1–§12) with evidence

| # | v0.1 statement | v0.2 | Evidence |
|---|---|---|---|
| 1 | repo private, README only (§1.3) | public, `docs/` + `validation/`, no LICENSE | `gh api` |
| 2 | `REQ-IN-5` treats all size limits as a warning | empty or ≥ 199 999 bytes → error; only 1024 cutoff → warning | `oef2wims.c:171,429–430` |
| 3 | CR and control chars 1–6 replaced | CR and bytes 0–6 | `oef2wims.c:143–165` |
| 4 | `REQ-IN-7` dynamic templates "partiel or echec" | `partiel` (G-06); `echec` only `--strict` or compiler refusal | §4.1, §14.2 |
| 5 | `REQ-LANG-1` no `<description>` | empty `<description/>` always emitted | RNG 93–94; fixtures |
| 6 | `REQ-EXPR-4` wrapped trig args by `×180/π` by default | trig is gap G-21 unless `--trig-units` is given (`deg` or `rad`, no default) | invents logic otherwise; `MAPPING.md:22` |
| 7 | §8.2 numeric/radio/checkbox/correspond/reorder class D | A† (structure direct, semantics unverified) | §8.5, Q5 |
| 8 | §8.2 counts `case` [0], `nocase…raw` [4], `reorder` [0] hand-written | [1], [6], [2] | `corpus_stats.json` `answer_type_files` |
| 9 | §8.1 `\choice` accepts `type=`; prompt overflow an error | no `type=`; `\choice` prompt silently truncated, `\answer` prompt ≥ 40 is an error | `process.c:293,354–,396` |
| 10 | `REQ-REP-4` count invariant | I1–I3 over source units, `copies(q)` for linearised steps | REQ-STEP-1 |
| 11 | placeholder carrier "orphan `text`, format assumed" | format verified on 2085 icons; carrier on `text` unconfirmed (Q5), switchable | catalogue, `1008.xml`, `3368.xml` |
| 12 | `REQ-OUT-5`, `REQ-TODO-4` depend on Schematron R05 | conditional on Q1; own `aucune_question` flag | handoff line 40 |
| 13 | `REQ-ARCH-4`: `oef2wims-v2.exe --json` (stdout implied) | writes `<name>.json` next to the log; gate on scratch copy; `-log` wrapper has no `--json` | `oef2wims_v2.c:196,350` |
| 14 | reserved names attributed to WIMS (`reply1…`, `pi`) | WIMS substitutes `\reply …` (7 names) and predefines `imagedir`, `confparm1…4`; `_v` suffixing is `xml2oef`'s own rule | `oeflines.c:111–138`; `MAPPING.md:17` |
| 15 | `-debug` of `oef2wims` as a diagnostic | `oef_debug()` is never called | `oef2wims.c:127` |
| 16 | M-45, M-21, G-07 table cells contained a literal pipe character | rewritten | — |
| 17 | corpus statistics tiers M1/M2/M3 counted `hint/help/solution`, `matrix` as covered | single tier `M1_mvp_scope` (phase-1 scope); final-scope bounds in `scope_bounds.py` | §14.2 |

### C.4 Cross-reference check

`check_refs.py` extracts every `§n[.m]`, `Qn`, `SC-n`, `AC-n`, `REQ-…`, `M-nn`, `G-nn`, `Rn` and `Appendix X[.n]` reference from the document and verifies that a matching definition (heading, table row or requirement) exists. Result for v0.2 (2026-11-09): **all references resolve** (61 numbered sections/subsections, appendix ids A, A.1–A.3.5, B, B.1, B.2, C, C.1–C.4, Q1–Q13, SC-1…SC-5, AC-1…AC-13, M-nn ×43, G-01…G-22, R1…R12, 74 `REQ-` ids). A negative control with deliberately broken references makes the script exit non-zero. The script also asserts that Q1–Q11, Appendix A.3 and Appendix B.2 exist. It is re-run before every release of this document.

*End of document.*
