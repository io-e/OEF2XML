# OEF2XML — Requirements improvement proposal v0.3.0

**Status:** Proposed normative amendment; not merged into `main`  
**Date:** 2026-11-10  
**Repository:** https://github.com/io-e/OEF2XML  
**Baseline:** `docs/CAHIER_DES_CHARGES_OEF2XML.md`, v0.2.5, commit `fdeb2b8d246af7699ea3b72b546f15299f51ab80`  
**Purpose:** Strengthen correctness, auditability, security and release gates without replacing the existing OEF mapping tables or corpus evidence.

> **Integration rule:** This is an amendment to the 1,348-line v0.2.5 specification, **not** a substitute for it. Existing definitions and Appendices A–C remain normative unless a replacement is explicitly identified below. Proposed new IDs begin with `REQ-REV-`, `AC-REV-`, or `R-REV-` to prevent conflicts. When merged, the original file should be revised in place, its changelog incremented, and cross-references regenerated. The scope remains OEF (WIMS 4.31b) → XML program (`urn:eleda:program:v1`, root `<eleda-program>`). The *target platform* remains distinct from the XML format.

## 1. Evidence-based audit: what must be corrected first

The current specification is unusually detailed and records important limits: only **121** of the **1,433** analysed non-test OEF files are ordinary upstream hand-written exercises; **212** are upstream model templates and **1,100** are generated from the forward converter. The 1,116 XML programs used for block-shape analysis do not establish target-platform grading semantics. These distinctions **must remain**.

| Priority | Location in v0.2.5 | Finding | Required correction |
|---|---|---|---|
| **P0** | §4.4, §8.4, AC-8 | A file can be `complet` although approximation of `\precision`, `\range`, `weight=` or answer options could change grading. | Separate structural completeness from grading equivalence. Missing grading semantics must block *deployability*; high-risk changes must not be described as safe. |
| **P0** | §6.3 M-48, §12 | `--html pass` preserves arbitrary HTML, while G-19 explicitly covers `<script>`, `<form>`, `<input>`. No mandatory hostile-content policy. | Make strict/sanitized HTML the default and quarantine executable/unsafe HTML. |
| **P0** | §13, §14 | RNG/XSD + shape lint do not prove that XML imports, runs, or grades correctly. The current manual criterion allows up to 6 of 30 files to fail C1–C5. | Add an independent publication gate; zero critical semantic defects. Keep schema validation as a lower-level check. |
| **P0** | §4.1, §11.2 | The compiler is run on a temporary copy but no timeout, resource bounds or safe copy of referenced assets/dependencies is specified. | Add an explicit subprocess threat model, sandbox limits, and distinction between syntax failure and unavailable dependencies. |
| **P0** | §6.5 REQ-TODO-1/6 | The TODO icon may hold only 4,000 characters, yet the specification requires the *verbatim complete fragment* and hash verification. An orphan block may be discarded by an importer. | Keep a full-fidelity sidecar manifest; use icons only as a human-readable preview. Test import/export retention. |
| **P0** | §12.2 | `<stem>.xml` collides for two input files with the same basename in different folders, or on case-insensitive filesystems. | Define collision-resistant relative-path output and an explicit collision policy. |
| **P1** | §4.1 REQ-IN-3 | Latin-1 and CP1252 cannot be unambiguously inferred merely from failed UTF-8 decoding. | Deterministic fallback, confidence/ambiguity flag, explicit override, preservation of original bytes. |
| **P1** | §7.3 REQ-EXPR-4 | Forward and inverse trig functions are handled as if one argument-unit conversion covered both directions. | Specify input and output unit conversions separately; require executable witness tests before mapping. |
| **P1** | §13.3 N3/N7 | Normalization can conflate `\x2oN` with `\x2orepN` and can erase meaningful whitespace from statements. | Use scope-aware, bijective renaming and preserve meaningful text/HTML whitespace. |
| **P1** | §4.4, §13.5 | “Byte-identical report” conflicts with `--stamp`, absolute paths, environment differences, and unpinned tool versions. | Define reproducible core artifacts and separate a mutable run manifest. |
| **P1** | §12.1 | `--validate none` and `--gate none` are permitted but not clearly barred from release. | Explicit modes: `inspect`, `convert`, `verify`, `publish-check` with distinct gates. |
| **P1** | §17 Q1/Q5 | Key source artifacts and target runtime are missing; the document has enough detail to appear implementation-ready even where semantics are unknown. | Introduce decision records and a machine-readable blocker register with owners and evidence. |
| **P1** | `tools/corpus_stats/check_refs.py` | Default filename points into `tools/corpus_stats/`, not `docs/`; a check contains `or True`, making one reference condition vacuous. | Fix both defects and test the validator with broken references. |
| **P2** | README, §11, §15 | The repository README is only a heading; no converter exists yet; no dependency lock or release provenance specification. | Add onboarding, package/CI conventions, manifests, reproducible test subsets and release checklist. |

### Non-negotiable preservation rules

- Never silently drop or fabricate an OEF directive, answer, algorithm, randomization rule, scoring rule or dependency.
- Do not rename `urn:eleda:program:v1` or `<eleda-program>`.
- Do not equate a schema-valid document with an importable or executable exercise.
- Do not conflate OEF generated by `xml2oef` with OEF authored by teachers.
- Preserve the existing `complet`/`partiel`/`echec` and `fidelite` fields for consumers of existing reports; add independent safety and verification dimensions.
- Treat missing target-platform grading evidence as **unknown**, not as evidence of equivalence.

## 2. Revised goals and boundaries (replaces §1.2 goal wording)

**Goal.** Convert syntactically accepted WIMS OEF files into deterministic XML program artifacts with traceable source-to-output mappings, comprehensive accounting of any unsupported behavior, and explicit readiness criteria for import, execution and assessment use.

Success is measured along **four independent axes**:

1. **Coverage:** was each source unit converted, approximately converted, documented as metadata, or isolated as an unsupported fragment?
2. **Structural validity:** is the XML well-formed, schema-valid, block-shape-valid and internally consistent?
3. **Semantic evidence:** has the conversion preserved randomization, statements, accepted-answer sets, conditions, feedback and assessment behavior, and at what level was that established?
4. **Deployment readiness:** may this file be imported into an authoring workspace or published to learners?

No aggregation may hide the distinction between these axes. The converter does not implement `wims.cgi` or invent exercise content. A `complet` file is structurally complete, **not automatically safe to publish**.

## 3. New normative requirements

### 3.1 Raw source, parsing, encoding and provenance

**REQ-REV-IN-1 — Immutable source evidence.** The converter MUST calculate the SHA-256 digest of the original OEF byte stream before decoding. Every AST/IR node that comes from the source MUST retain a source span with byte start/end offsets and decoded line/column positions. The unmodified source MUST remain untouched. Reports MUST retain the original file digest, size and line-ending profile.

**REQ-REV-IN-2 — Encoding ambiguity.** Detection order: BOM → strict UTF-8 → configured fallback encoding. When both ISO-8859-1 and CP1252 are plausible, `auto` MUST use a documented deterministic preference (proposed: CP1252 when undefined code points are absent; otherwise ISO-8859-1), set `encodage_confiance="faible"`, and record the alternative. The CLI `--encoding` overrides detection. A strict mode MUST reject unresolved ambiguity. Decoding must not use silent replacement characters.

**REQ-REV-IN-3 — Lexical separation.** The lexer MUST distinguish directives, quoted/escaped text, mathematical expressions, comments, HTML segments and WIMS substitution contexts. Context-sensitive syntax MUST NOT be flattened by regex-only preprocessing. A malformed file may produce diagnostics, but no speculative repaired output.

**REQ-REV-IN-4 — External dependencies.** Track all external references (`slib`, `mdef`, `imagedir`, `filedir`, fonts/media and OEF environment variables). Each receives `resolved`, `unresolved`, `unsupported` or `not_checked`; include its origin and any integrity hash of an available file. An unresolved dependency affecting a question MUST trigger taint and block publication.

**REQ-REV-IN-5 — Corpus provenance.** Every evaluation entry MUST identify one of `H` (121 hand-written upstream), `M` (212 model templates), `Gn` (1,100 generated), or `E-O` (future owner-authored). Metrics MUST be reported separately for each set, with the originating WIMS tarball, source path, and converter commit where applicable. Existing corpus numbers remain *baseline evidence*, not evidence of current converter performance.

### 3.2 Semantic model and soundness of mappings

**REQ-REV-SEM-1 — Typed, provenance-bearing IR.** Each IR node MUST include: `node_id`, source span, source raw fragment, value/statement/question type, execution phase (`pre`, `post`, `answer`, or `display` where relevant), dependencies, mapping ID, conversion disposition, and verification level. Evaluation order and short-circuit behavior MUST be preserved. The IR schema MUST be versioned independently of the XML schema.

**REQ-REV-SEM-2 — Taint across all grading inputs.** Taint MUST propagate through expected answers, answer-type selection, answer options, weights, tolerance/precision, ranges, comparisons, feedback predicates and step progression—not only through declared variables. Any unverifiable grading-relevant source unit MUST set `evaluation_risk=true` for every affected question. Such a question is NOT publishable without explicit reviewed evidence.

**REQ-REV-SEM-3 — Fidelity evidence per mapping.** Every `M-nn` mapping MUST have an accompanying machine-readable record with: source construct; target block shape; assumptions; supported domains and edge cases; fidelity claim; authoritative evidence; sample fixtures; positive tests; negative tests; responsible reviewer; review status. A mapping MUST NOT be upgraded to `exacte` merely because its XML shape is present in the catalog.

**REQ-REV-SEM-4 — Answer-evaluation contract.** For every mapped answer class, specify what counts as equal: numeric precision/tolerance, units, string case, expression equivalence, ordering, multiple-choice partial credit, weights, number of attempts and feedback timing. Where either WIMS or the target platform is undocumented/unverified, use `non_verifiee` and set deployment to `BLOCKED` or `REVIEW_REQUIRED` according to the risk matrix. In particular, dropping `\precision`, `\range`, `weight=` or grading options is **not** an innocuous display approximation.

**REQ-REV-SEM-5 — Trigonometry directionality.** Distinguish `sin/cos/tan` (angles as *inputs*) from `asin/acos/atan` (angles as *outputs*). For the former, convert the argument from WIMS radians into the target's assumed input units. For the latter, convert the target function's *result* into WIMS radians when required; do NOT blindly convert its dimensionless argument. Composition and interval/branch conventions MUST be tested. Until verified by both engines (Q5/Q6), such mappings remain `non_verifiee` and are not publishable.

**REQ-REV-SEM-6 — Randomization reproducibility.** Preserve the distribution, admissible domain, inclusivity of endpoints, item ordering, replacement policy and relevant numeric precision for `random`, `randint`, `shuffle`, `randitem` and `pickone`. Equal seeds across systems are not assumed to yield equal draws; compare invariant distributions or sampled outcomes with a documented protocol. Never assert exact randomization from syntactic similarity alone.

**REQ-REV-SEM-7 — Behavioral dependencies.** Multi-step transitions, post-`\statement` definitions, answer-time `\reply`/`\sc_reply`, and `\condition` MUST be modeled as a dependency graph. A static linearization is allowed only if equivalence of the reachable step sequence is proven; otherwise classify as G-08 or G-15 and preserve the source.

### 3.3 XML emission, TODOs and assets

**REQ-REV-OUT-1 — Canonical identity.** Output names MUST be unique within a batch. Default: preserve input-relative directory structure below `--out`; same-relative-path and casefold collisions MUST cause a preflight error unless an explicit `--collision-policy hash-suffix` option is used. The input root and path-to-artifact mapping MUST appear in the manifest. The root `@id` MUST be validated for schema compatibility; two distinct inputs MUST NOT accidentally share an XML program ID.

**REQ-REV-OUT-2 — Complete TODO manifest.** The converter MUST produce one full-fidelity, UTF-8 `*.todos.json` sidecar per partial output, containing each unsupported or tainted fragment **in full**, original byte span and SHA-256, reason, mapping/gap ID, dependency chain and affected questions. The existing 4,000-character comment icon is a *preview only* and MUST contain a stable reference to the manifest entry. No full text may be silently truncated. The manifest MUST be considered part of the conversion artifact set.

**REQ-REV-OUT-3 — Placeholder survivability.** Orphan-block TODOs MAY be emitted only as an editable convenience. Before the target platform has been tested for orphan-block and icon preservation through import/export, **the sidecar manifest is the authoritative record**. A missing or modified placeholder is a validation failure. Never classify an icon-only TODO as safe-to-publish.

**REQ-REV-OUT-4 — HTML and media safety.** Default HTML policy is `--html strict`: allow only a documented, sanitized set of passive tags and attributes; prohibited active content such as `<script>`, forms, event handlers, `javascript:` URLs, untrusted iframes and dangerous `data:` URLs MUST become gaps, not emitted executable markup. No network downloads. Asset copying MUST reject path traversal, absolute references outside approved roots, symlink escapes and unsafe file types. Manifest all copied assets with digests. Explicit `--html unsafe-pass` MAY exist for isolated diagnostics but MUST force `publication=BLOCKED`.

**REQ-REV-OUT-5 — XML parser hardening.** Every parser used by the converter, validator or tests MUST disable external DTD/entity expansion, external network resolution, and unsafe XInclude. Apply explicit maximum file size, nesting depth and processing duration where supported. Schemas MUST be loaded only from pinned local locations. Malicious corpus examples MUST be tested.

**REQ-REV-OUT-6 — Schema provenance.** The report MUST record the full SHA-256 and local path of each RNG, XSD and Schematron actually used, and the exact schema profile (`v1`, or an explicit approved `v2` bundle). It MUST distinguish `NOT_PROVIDED`, `NOT_RUN`, `PASS`, `FAIL`. The `source_format="ir"` workaround is only a schema-conforming *serialization value* and MUST NOT be presented as the original provenance; record `source_format_original="oef"` in the report until SC-1 is approved.

### 3.4 Processes, batching, determinism and reports

**REQ-REV-RUN-1 — Safe compiler invocation.** Invoke a pinned local compiler binary via argument-array subprocess, never a shell command. Use a new temporary directory for each input, a restricted working directory, bounded CPU/wall time, memory and output size; capture exit code, stderr/stdout, compiler JSON and diagnostics. Clean scratch files by default. Detect and report when referenced resources are unavailable in scratch mode. A timeout is `GATE_TIMEOUT`, **not** evidence of malformed OEF.

**REQ-REV-RUN-2 — Gate honesty.** `--gate validator` is an offline approximation, not a successful `oef2wims` compilation. `--gate none` and `--validate none` are allowed only in inspect/diagnostic workflows. Neither may produce `publication=APPROVED`; the report MUST expose every skipped gate. An absent compiler MUST NOT be silently replaced by the validator while continuing to claim compiler proof.

**REQ-REV-RUN-3 — Atomic outputs.** Stage XML, TODO manifest, logs and reports in an output staging directory, validate all staged artifacts, then atomically rename individual files into place. On failure, do not leave a partially written XML that could be mistaken for valid output. `--force` MUST apply only to *generated output paths*, never to source OEF files. Preflight all collisions before work begins.

**REQ-REV-RUN-4 — Deterministic core vs runtime metadata.** Core XML, deterministic IDs, normalized report and TODO manifest MUST be byte-identical for equal input bytes + option set + converter/tool versions + schema hashes. Wall-clock timestamps, absolute scratch paths, durations and machine information belong in a separate `run-manifest.json` and are excluded from deterministic comparison. `--stamp` explicitly opts out of byte-for-byte output determinism and MUST be reported.

**REQ-REV-RUN-5 — Machine-readable diagnostics.** Add `code`, `severity`, `source_span`, `source_sha256`, `rule_id`, `affected_question_ids`, `recovery`, and `evidence_level` to report details. Preserve existing French JSON keys for compatibility and add `report_schema_version` (`2` proposed). Diagnostics MUST distinguish unsupported construct, unsafe approximation, missing dependency, compiler error, XML error, internal defect and test-oracle limitation. Errors MUST be stable and suitable for filtering in CI.

**REQ-REV-RUN-6 — Audit outputs and confidentiality.** Full snippets and exercise solutions can be sensitive. Default logs MUST be local only, with no telemetry; offer `--redact-report` for externally shared reports. Redaction MUST retain hashes, spans and gap counters. The converter MUST never send source content to a remote service.

### 3.5 Delivery modes and publication policy

**REQ-REV-REL-1 — Explicit modes.** Define the following CLI commands (or equivalent `--mode`):

| Mode | Purpose | Minimum required checks | Publishable? |
|---|---|---|---|
| `inspect` | Parse, inventory, identify gaps without emitting XML | G0, corpus/encoding provenance | No |
| `convert` | Produce XML and reports | G0 + XML/shape validation where available; skipped gates explicit | No, by itself |
| `verify` | Run available compiler, schema, invariants, round-trip and optional runtime oracles | G0–G3 + test evidence | Evidence only |
| `publish-check` | Decide import/publication readiness from signed/approved evidence | All mandatory gates, no unresolved critical questions | Yes, only if `APPROVED` |

**REQ-REV-REL-2 — Three-valued publication state.** Add `publication ∈ {BLOCKED, REVIEW_REQUIRED, APPROVED}` to reports. `APPROVED` requires a successful real import into the target platform, an assessment-contract verification for every question, all source-unit accounting invariants, all mandatory checks passing, and no unresolved critical gap, taint, unsafe HTML or compiler failure. An absent runtime or target semantics produces `REVIEW_REQUIRED` or `BLOCKED` (never `APPROVED`). A teacher may approve a *remediated* exercise only in a separate review workflow with a new artifact hash; the original conversion is not silently upgraded.

**REQ-REV-REL-3 — Version-pinned evidence.** Each approved release MUST identify: OEF source hash; converter version and Git commit; Python and `lxml` versions; WIMS compiler SHA-256 and version; source corpus category; schema bundle hashes; target platform version; mapping catalog hash; manual review sign-off, if any. Store these in a release manifest alongside tests.

**REQ-REV-REL-4 — Acceptance independence.** Conversion completeness rates are **coverage KPIs**, not quality proof. A file may be counted as `complet` for coverage but fail publication. Failing the source compiler, structural validation, no-silent-loss invariants, or a critical semantic equivalence check MUST defeat release regardless of corpus-wide percentage.

## 4. Revised report contract (§4.4 additive changes)

Retain `outil`, `resume`, `fichiers`, `statut`, `fidelite`, `questions_*`, `blocs_question_emis`, `non_traduits`, `approximations`, `details`, and the `complet` / `partiel` / `echec` values. Add the following example fields (illustrative, not an observed tool output):

```json
{
  "report_schema_version": 2,
  "outil": "oef2xml 0.3.0",
  "fichiers": [
    {
      "source": "lesson.oef",
      "source_sha256": "<64-character SHA-256>",
      "sortie": "lesson.xml",
      "statut": "complet",
      "fidelite": "non_verifiee",
      "publication": "BLOCKED",
      "evaluation_risk": true,
      "evidence": {
        "compiler": "PASS",
        "rng": "PASS",
        "xsd": "PASS",
        "schematron": "NOT_PROVIDED",
        "shape_lint": "PASS",
        "target_import": "NOT_RUN",
        "grading_equivalence": "NOT_RUN"
      },
      "gaps_manifest": null,
      "details": [
        {
          "code": "GRADING_PRECISION_UNVERIFIED",
          "severity": "critical",
          "rule_id": "REQ-REV-SEM-4",
          "affected_question_ids": ["q1"]
        }
      ]
    }
  ]
}
```

**Interpretation:** `complet` and `publication=BLOCKED` are intentionally compatible: a structurally complete migration may have unverified grading semantics.

A complete report schema MUST be published as JSON Schema, with golden fixtures and explicit migration rules from current report fields. TSV remains the default tabular output because the current CLI already names it `FILE.tsv`; the section title should read **“JSON and TSV”**, not “JSON and CSV”.

## 5. Revised validation and evaluation protocol (§13)

### 5.1 Test pyramid

1. **Parser differential:** compare accept/reject, directive boundaries, parameter trees and diagnostics against the pinned WIMS 4.31b compiler. Preserve known compiler silent-acceptance behavior as warnings, never as inferred correctness.
2. **Schema and shape:** RNG + XSD + approved Schematron, plus explicit grammar of each emitted block. Cover malformed XML, unknown fields, wrong child order, invalid IDs, broken references, orphan comments and schema-profile drift.
3. **Semantic unit tests:** table-driven golden input/output for every `M-nn`, `G-nn`, answer class and special function, including negative tests and source-coverage invariants.
4. **Metamorphic/property tests:** randomization bounds, list operations, equivalent expression parenthesizations, encoding invariance, repeated conversion, path renaming, step ordering, failure injection and fuzzed brace nesting.
5. **Round-trip:** retain RT-A, RT-B, RT-C. Diff comparison MUST be conservative: a normalization rule may never erase changed answer types, expected-answer text, tokens of LaTeX, choice order, HTML-sensitive spaces or the distinction between `\x2oN` and `\x2orepN`.
6. **Target runtime:** real XML import/export, statement rendering, sample generation and grading for correct, incorrect, boundary and partial-credit responses. Record the exact target version and inputs.
7. **Human review:** stratified teacher review of at least 30 upstream hand-written files covering every common answer class, major gap family and any high-risk mapping.

### 5.2 Exact changes to RT normalization

- **N3:** use *namespace-specific* bijective renaming (`x2oN` vs `x2orepN`) and lexical scope. A source temporary reused with different meaning MUST NOT be equated.
- **N7:** compare statements as tokenized semantic HTML and structured LaTeX spans. Whitespace is normalized only where demonstrably ignorable; `<pre>`, code, text nodes containing significant separation, and TeX token boundaries remain significant.
- Add an **N9 safety rule:** normalization is forbidden to change the ordered multiset of answer types, solution strings, grading options, question-to-embed associations or gap counts.
- Every `DIFF-EXPLAINED` MUST point to at least one report detail with a source/output span. Explanations are not generic exemptions for missing content.

### 5.3 Manual-review gate

Replace the single “≥24 of 30 pass C1–C6” gate with:

- **0 critical errors** in statement meaning, variables/randomization, expected answers, answer types, grading options, taint or fabricated logic across the 30-file sample.
- **100%** of unsupported constructs in the sample accounted for in the TODO manifest, with full fragments and source hashes.
- **≥90%** of the sample may pass presentation-quality criteria (typography/layout), with every failure logged and no critical semantics impacted.
- Every supported answer class and each P0 mapping must have a dedicated reviewed fixture; a sample that omits a class is not sufficient.

### 5.4 Additional acceptance criteria

| ID | Criterion | Evidence | Gate |
|---|---|---|---|
| AC-REV-01 | 100% of source units and question units have exactly one disposition, with byte spans and SHA-256 provenance | IR audit, I1–I3, independent XML scan | P1 |
| AC-REV-02 | No batch path collision, source overwrite, partial output or asset path escape | Windows/Linux adversarial path suite | P1 |
| AC-REV-03 | 100% of partial files have complete full-text TODO manifests with source span/hash; orphan TODOs are unreachable | sidecar lint, importer round trip where available | P1 |
| AC-REV-04 | No executable HTML or external entities emitted or resolved under default options | malicious fixtures and parser tests | P1 |
| AC-REV-05 | Every compiler invocation is bounded, recorded, isolated and cleaned up; timeout/missing dependency have distinct error codes | sandbox/failure-injection tests | P0/P1 |
| AC-REV-06 | Core XML, report and TODO manifests are byte-identical for repeated runs with pinned versions/options; timestamp data is external | deterministic rebuild suite | P1 |
| AC-REV-07 | No file is marked `APPROVED` without verified real target import and assessment behavior for all questions | publish-check negative controls | P3 |
| AC-REV-08 | No critical semantic error in the manual 30-file E-H sample, with at least 90% presentation pass rate | signed review register | P3 |
| AC-REV-09 | All `M-nn` rows have mapping records with fixtures, assumptions and reviewer evidence | mapping coverage tool | P2/P3 |
| AC-REV-10 | Reference checker catches missing IDs and uses the correct default document path | mutation tests + CI | P0 |

### 5.5 Existing thresholds and caveat

Keep the *per-corpus* thresholds of §14.2 as **coverage milestones**, explicitly conditional on the stated scope bounds and sampling frame. Do **not** rename them to semantic-equivalence thresholds. Maintain the important warning that the MVP hand-written gate has only **5** eligible files. Any unexplained result exceeding the mathematical upper bound must trigger an investigation, not an automatic rejection of improved support; the bound itself may have become stale after mapping changes.

## 6. Updated implementation roadmap (§15)

| Milestone | Deliverables | Exit gate |
|---|---|---|
| **P0a — Specification and source audit** | Correct contradictions and broken reference checker; risk register; strict threat model; record schema/runtime availability; pin baseline commit and compiler hash | Cross-reference negative controls pass; decisions logged |
| **P0b — Foundations** | Shared lexer/AST; source spans, encoding detection; IR JSON Schema; mapping and diagnostic registries; report v2 JSON Schema; safe compiler adapter | Differential compiler samples; AC-REV-05 |
| **P1 — Safe conversion MVP** | CLI, deterministic emitter, shape lint, sanitized HTML, full-fidelity TODO manifest, taint on scoring settings, atomic outputs, collision-safe paths | Original MVP coverage gate + AC-REV-01–04,06 |
| **P2 — Extended mappings** | Lists/matrices where evidenced, expressions, six `wims()` subcommands, selected CAS/markup; trig only with verified units; coverage fixtures per mapping | P2 coverage KPIs + AC-REV-09 |
| **P3 — Semantic validation** | Target runtime adapter, sample generation/grading oracle, RT-A/B/C, audited teacher sample, publication checks | AC-REV-07/08 plus original AC-9/10 |
| **P4 — Optional UX** | PyInstaller, web interface, visualization of gaps, guided manual remediation outside converter, versioned XML schema upgrade | Separate decision; cannot weaken P1–P3 safety gates |

**Rule:** Unsupported mappings must not block the entire project; they produce a safe partial conversion. Conversely, high completion percentages never compensate for wrong answers or missing scoring constraints.

## 7. Open decisions and blockers (supplements Q1–Q13)

| ID | Decision needed | Default and consequence | Owner evidence required |
|---|---|---|---|
| D-01 | Supply approved XML program v2 RNG/XSD/DTD/Schematron bundle and hashes | Use pinned v1 only; Schematron `NOT_PROVIDED`; do not claim v2 parity | Schema bundle + expected negative fixtures |
| D-02 | Supply target-platform importer/exporter and grading API or test harness | No `publication=APPROVED` | Versioned runtime/build + sample exercises |
| D-03 | Confirm `math_trig` forward and inverse unit conventions | All trig mapping unverified; high-risk questions blocked | Controlled input/output experiments |
| D-04 | Define default grading/attempts policy for imported exercises | `max_attempts=1` only as explicit default; grading equivalence not assumed | Product decision + runtime test |
| D-05 | Approve TODO preservation format and authoring workflow | Sidecar is authoritative; orphan icon only a preview | Round-trip import/export evidence |
| D-06 | Define approved HTML subset and image URI policy | Strict sanitization and offline assets | Security policy + fixtures |
| D-07 | Supply additional owner-authored hand-written OEF evaluation corpus E-O | E-H evidence only; no claims about owner-specific coverage | Consented, licensed files + provenance |
| D-08 | Set binary redistribution/licensing rules for compiler and assets | Local binaries, hashes, licenses documented; no bundled binary by default | Licence review and NOTICE/SBOM |

Each decision should have `status={OPEN,DECIDED,VERIFIED}`, assignee, timestamp, evidence URI/hash, affected `REQ`/`M`/`G` IDs and re-review trigger.

## 8. Targeted repository fixes

These are **specific defects or hygiene improvements** observed in the current repository, independent of the converter implementation:

1. **`tools/corpus_stats/check_refs.py`:** change the default spec path to `Path(__file__).resolve().parents[2] / "docs" / "CAHIER_DES_CHARGES_OEF2XML.md"` (instead of searching in the script directory). Remove `or True` from the `REQ-MAP-Q-TEMPLATE` existence check. Make missing ID definitions fail, and add two negative controls to CI. Avoid counting a reference as its own definition.
2. **`docs/CAHIER_DES_CHARGES_OEF2XML.md`:** §12.1 `--placeholder-carrier` claims default `text`; the changelog describes a move to `display_element`, while §6.5 still documents `text` as default. Choose one after importer testing; do not state both. In either case, the full sidecar is mandatory.
3. **Status line:** replace “Nothing in this document has been implemented” with “No OEF→XML converter has been implemented; the OEF validator, compiler wrappers, schema test fixtures and corpus tooling are already present.”
4. **§1.3 and Appendix C:** revise stale repository timeline, `LICENSE` statements, artifact paths and references to old v0.2 filenames. Keep baseline evidence separated from newly verified results.
5. **§4.4:** rename “JSON and CSV” to “JSON and TSV”; publish `report.schema.json` plus backward-compatible fixtures.
6. **`validation/xml/tests/run_schema_tests.py`:** use a hardened `lxml.etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True, huge_tree=False)` for fixtures and for any untrusted user XML. Add invalid XML entities, nested-depth, invalid-block, invalid-reference and unexpected-attribute tests. Because the v1 schema allows unknown block types, explicitly test that schema validation **accepting** an unknown type is caught by shape lint.
7. **README:** document goal, pipeline, non-goals, prerequisites, status, licensing, reproduce-schema-tests command, source provenance and meaning of `complet`, `fidelite` and `publication`.
8. **Build metadata:** introduce `pyproject.toml`, pinned dependencies/lock file, `pytest`, CI jobs for Windows/Linux, `ruff` or equivalent linting, `mypy` or equivalent typing checks, and supply-chain provenance for releases.

## 9. Definition of done

OEF2XML can be called a **converter MVP** when it safely parses and emits the phase-1 scope, accounts for every source/question unit, produces a validated XML program and complete TODO sidecars, has no silent loss, and meets the original P1 corpus-specific coverage targets with deterministic and secure behavior.

OEF2XML can be called **production-ready for student exercises** only when the target platform's importer, rendering, randomization and grading behavior have been verified; each published artifact is backed by hashes and evidence; and **no published exercise contains an unresolved critical grading or semantic defect**. Until D-01/D-02 and relevant grading contracts are resolved, `publication=APPROVED` is not available.

---

### Source files consulted

- Main requirements v0.2.5: https://github.com/io-e/OEF2XML/blob/main/docs/CAHIER_DES_CHARGES_OEF2XML.md
- Cross-reference checker: https://github.com/io-e/OEF2XML/blob/main/tools/corpus_stats/check_refs.py
- Schema fixture runner: https://github.com/io-e/OEF2XML/blob/main/validation/xml/tests/run_schema_tests.py
- Validation README: https://github.com/io-e/OEF2XML/blob/main/validation/README.md
- Main repository: https://github.com/io-e/OEF2XML

**Review status:** This amendment is based on inspection of repository contents and code, not an executed test of the complete repository or a functioning OEF→XML converter. Numerical baseline figures are retained from v0.2.5 and have not been independently recomputed here.
