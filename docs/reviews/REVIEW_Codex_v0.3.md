# Review of "OEF2XML — Requirements improvement proposal v0.3.0" (Codex)

Reviewed: `/workspace/codex_v03/OEF2XML_Requirements_Improvement_v0.3.md` (277 lines)
Against: spec v0.2.5 at `origin/main` = `fdeb2b8d246af7699ea3b72b546f15299f51ab80` (read with `git show`, saved as `spec_v025.md`)
Implementation read from branch `p0-p1` (`5b744cd`) through `git show` / `git archive` into `/tmp/p01` (read-only; nothing in `/workspace/OEF2XML_repo` was touched).
Checks run: `check_refs.py` mutation tests (on a copy in `/tmp/cr`), the p0-p1 CLI on adversarial inputs and on the 1438-file corpus with `--gate none` (output in `/tmp/p01`), and greps of the WIMS 4.31b sources.

Class legend: **ADOPT** = correct and new · **ADOPT-AMENDED** = good idea, needs the stated fix · **COVERED** = v0.2.5 already says it · **REJECT** · **DEFER** (P2/P3/P4).
P1 impact legend: `none` · `small` (additive, under about half a day, no redesign) · `rework` (design change).

---

## 0. Verdict in five lines

1. Codex's proposal is useful, but about 60% of it is either already in v0.2.5 or is scope creep (a `publication` state, `publish-check` mode, `run-manifest`, a decision register, a redaction option). The solid content is about 12 targeted hardening points, plus the four defects you had already verified.
2. Nothing Codex asks for invalidates the work already on `p0-p1`. A few additions are needed (collision handling, gate honesty, TODO > 4000 characters, `--html` active-content list, report hash fields). Per-node IR provenance (SEM-1), the CLI modes (REL-1) and `publication` (REL-2) would force rework. They should be rejected.
3. Codex is right about the trig direction, but misses `acos` (no `ACOS` in `math_trig`) and the WIMS aliases. The spec also lacks the inverse forward idiom `asin(x)*180/pi`.
4. Two real spec contradictions that Codex only half-sees. First, REQ-REP-3 says `complet` means "nothing lost", while M-07/G-05 drop `\precision`, `weight=` and others as "approximation". Second, M-48 says `<script>/<form>` are carried verbatim, while G-19 says they are gaps.
5. Defects confirmed on `p0-p1` that no one listed: gate fallback reports `compilateur: ok` when no compiler ran, case-insensitive output collisions overwrite files, two inputs can get the same program `@id`, and stale `.xml` files survive an `echec`.

---

## 1. Re-verification of the four defects you confirmed

| # | Claim | Result |
|---|---|---|
| 1 | `check_refs.py` default path + `or True` | **Confirmed.** The default is `<script dir>/CAHIER_DES_CHARGES_OEF2XML.md`, which does not exist (running with no argument gives FileNotFoundError). Line 44 ends `… or True`. Nuance: removing `or True` changes nothing today, because the heading `### 8.3 … (REQ-MAP-Q-TEMPLATE)` is within the first 300 characters of the `split('### 8.3')[1]` text, so the check is dead, not hiding a failure. Codex's "make missing IDs fail" is **already true**. A mutation that changes only one reference (`REQ-ARCH-4` → `REQ-ARCH-44` in AC-11) exits 1, and removing the Q6 row hits the `assert`. Only the `-Q-TEMPLATE` check is vacuous. Codex's suggested path `Path(__file__).resolve().parents[2]/"docs"/…` is correct for `tools/corpus_stats/check_refs.py`. |
| 2 | Changelog line 41 says carrier → `display_element`; REQ-TODO-1 and CLI say `text` | **Confirmed** (line 41 in "Changelog v0.1 → v0.2"). C.3 row 11, REQ-TODO-1, §12.1, R10 and `p0-p1` all say `text` by default and switchable. Fix: edit line 41 to say "`text` default, switchable". Do not "choose after importer testing" as Codex suggests, because Q5 cannot be tested now. |
| 3 | `--html pass` default carries `<script>/<form>/on*` verbatim | **Confirmed in the spec** (M-48 lists `<script>`, `<form>` as carried verbatim; §12.1 default `pass`; G-19 says gap, so the spec contradicts itself). **In `p0-p1` code**: `<script>`, `<form>` and `<input>` are *already* always G-19 gaps (`textparse.py` lines 155–158). But `on*=` attributes, `javascript:` hrefs and `<iframe>` are still carried verbatim under `--html pass` (tested: `<div onclick=…>`, `<a href="javascript:…">`, `<iframe src=…>` all land in the `text` field). Measured on the whole 1438-file corpus: `<script>`/`<form>`/`<input>`/`on*=`/`javascript:`/`data:` = **0 files**; `<iframe>` = **12 files**, all generated-set files with YouTube embeds from your own programs. So the risk is theoretical on this corpus, and a blanket "iframe → gap" would turn 12 of your own Gn files `partiel`. That choice is yours. |
| 4 | Inverse trig direction | **Direction settled** (table below). Your first formulation was right ("with `deg`, the result of `asin/atan` needs ×π/180"). The parenthetical "×180/π" in the brief is the *forward* direction (XML→OEF) and is wrong for OEF→XML. Also confirmed: the catalogue's `math_trig` `OP` values are SIN 333, COS 332, ATAN 43, TAN 30, ASIN 28, with **no ACOS**. REQ-EXPR-4 lists `acos`, but §5 line 234 lists `SIN COS TAN ASIN ATAN`. `acos` therefore can never be emitted. |

**Trig, correct rules (OEF → XML).** WIMS always works in radians (`sin(x)`, `asin(x)` with x in rad; `asin` returns rad). The unit of the target platform is given by `--trig-units`.

| OEF call | `--trig-units rad` | `--trig-units deg` |
|---|---|---|
| `sin/cos/tan(x)` | `math_trig(x)` | `math_trig(x×180/π)`; the idiom `sin(x*pi/180)` → `math_trig(x)` (current B.2) |
| `asin/atan(x)` | `math_trig(x)`; the argument is dimensionless | `math_trig(x)` returns **degrees**; the OEF value is radians, so wrap the result: `math_trig(x) × π/180` |
| forward idiom `asin(x)*180/pi` (what `xml2oef` emits, `translate.go:496`) | keep the expression | strip `*180/pi` → plain `math_trig(x)` |
| `acos` | gap (no block shape) | gap (no block shape) |

Facts checked: forward converter `translate.go:495–498` gives `asin(x)*180/pi` and `sin(x*pi/180)`. B.2 of the spec lists only the `sin` idiom, so the inverse idiom is a spec hole. WIMS `Lib/evalue.c:205–270` also accepts `arcsin arccos arctan arctg tg ctg cot cotan sec csc` and the hyperbolics; REQ-EXPR-4 and G-21 name only `sin cos tan asin atan acos`. The unlisted aliases should be gaps (G-11), and arcs should be recognised under all their names.
`p0-p1` status: `expr.py:89–304` already makes `asin/acos/atan/arc*` always G-21 and maps only `sin/cos/tan`. So the code is **safe and needs no rework**; only the spec needs the table above for P2.

---

## 2. Codex's 28 requirements

### 2.1 Raw source, parsing, encoding, provenance

| ID | Class | Reason / what v0.2.5 says / required fix | P1 impact |
|---|---|---|---|
| REQ-REV-IN-1 Immutable source evidence | **ADOPT-AMENDED** | Already there: `octets`, `encodage`, `ligne_oef/colonne_oef` (REQ-REP-2), SHA-256 of each TODO fragment (REQ-TODO-1), no write to sources (REQ-BATCH-2). New and cheap: `source_sha256`, size and EOL profile (LF/CRLF/CR/mixed) per file in the report. Not as written: "every IR node retains byte start/end offsets". Decoded text for 267 ISO-8859 files makes byte offsets differ from char offsets, and `p0-p1` positions are char offsets into the normalised text. Keep line/col (+ char offset) on gaps and placeholders only. | small (3 report fields) |
| REQ-REV-IN-2 Encoding ambiguity | **ADOPT-AMENDED** | REQ-IN-3 does say "else ISO-8859-1/cp1252" without an order. `decode.py` already does BOM → strict UTF-8 → strict cp1252 → latin-1, which is exactly Codex's "proposal". Measured: of the 267 non-UTF-8 files only **2** (`00210`, `00252`) contain bytes 0x80–0x9F, the only place latin-1 and cp1252 differ. Fix: write the order into REQ-IN-3; add `encodage_ambiguite` only when such bytes occur (otherwise no ambiguity exists); `--encoding` override already exists. "Strict mode rejects ambiguity" can be tied to `--strict`, not a new mode. | none (doc + one flag) |
| REQ-REV-IN-3 Lexical separation | **COVERED** | §11.2 steps 1–3 (port of `process()`, `find_matching`), REQ-EXPR-1/6 (real parser, no best-effort tree), §7.5 (never repair). "Not regex-only" is a design opinion, untestable, and `p0-p1` uses regexes for HTML tag matching in `textparse.py`. Do not copy the wording. | none |
| REQ-REV-IN-4 External dependencies | **COVERED** | REQ-IN-6 (slib dependency list, `imagedir/filedir` as asset references, predefined names), G-13 (placeholder + taint), §7.6 (`assets[]`). The per-asset status enum and hash belong with `--assets-dir` (P2). "block publication": there is no such concept (see REL-2). | none |
| REQ-REV-IN-5 Corpus provenance | **COVERED** | §2.2, §14.2 (H/M/Gn per-corpus metrics), `corpus.map`, `per_file.csv`, E-H/E-M/E-O in §13.3. Tiny extra: gate/evaluation reports record the converter commit. | none |

### 2.2 Semantic model

| ID | Class | Reason / fix | P1 impact |
|---|---|---|---|
| REQ-REV-SEM-1 Typed provenance IR | **REJECT** (as written) | REQ-ARCH-1/2 already give a serialisable IR (`--dump-ir`) with `M-nn/G-nn` ids per detail, and §7.1 mandates `pre/post` phase tags. The extras (raw fragment, dependencies and "verification level" on **every** node; preserved short-circuit semantics; an IR schema versioned independently) would redesign the IR. The `p0-p1` IR is the *output block tree* with rule ids. Salvage: an `ir_version` field in `--dump-ir`. | **rework if adopted** |
| REQ-REV-SEM-2 Taint across grading inputs | **ADOPT-AMENDED** | REQ-TODO-3 taints variables defined by gaps; G-05/G-15/G-08 cover options, weights, conditions, steps. What is missing is the *flag*: a per-question `risque_evaluation` (true when `\precision`, `\range`, `weight=` or a grading option was dropped, or a condition/step was approximated). Keep it orthogonal to `statut`. Do not rename it `evaluation_risk` (the report keys are French). | small |
| REQ-REV-SEM-3 Fidelity record per mapping | **DEFER** (P2/P3) | Overlaps REQ-ARCH-2 (mapping data), REQ-REP-7 and §13.4 (golden XML per `M-nn`). "Reviewer, review status" is process overhead before the target platform exists. Note: `p0-p1` has no `mapping.yaml`; ids are hard-coded (REQ-ARCH-2 deviation to settle in P2). | none |
| REQ-REV-SEM-4 Answer-evaluation contract | **ADOPT-AMENDED** | §8.5, REQ-REP-7, R2 and Q5 already say grading semantics are `non_verifiee`. The new and valid point: dropping `\precision`/`\range`/`weight=`/options is not an "innocuous display approximation". Today REQ-REP-3 defines `complet` as "nothing was lost or isolated" yet M-07 and G-05 drop these with an "approximation" detail. That is an internal contradiction. Fix: reword REQ-REP-3, and expose the dropped items via the `risque_evaluation` flag (SEM-2). **Do not** demote such files to `partiel` without recomputing `scope_bounds.py` (66 upstream files use `\precision`), which would move every §14.2 bound. That is an owner decision. | small |
| REQ-REV-SEM-5 Trig directionality | **ADOPT-AMENDED** | Direction correct (see §1 table). Amend: acos is a gap (no `ACOS` block value); WIMS aliases; B.2 inverse idiom; "verified by both engines before mapping" must not block the opt-in `--trig-units`, which is the owner's explicit assumption (§15 P2: "trig behind `--trig-units`"). Branch conventions (principal values) are P3. | none (code already gap) |
| REQ-REV-SEM-6 Randomisation reproducibility | **DEFER** (P3) | §7.2 + M-10/M-11 + T2 in §13.3 already cover semantics and seeded comparison. Useful addition for Q5: is `random_number{min,max}` inclusive at both ends, as WIMS `randint(a..b)` is? M-10 is marked E while REQ-REP-7 says nothing is exact before Q5. | none |
| REQ-REV-SEM-7 Behavioural dependencies | **COVERED** | §7.1 (pre/post phase), §9 REQ-STEP-1/2/3 (static linearisation only for trivial `\nextstep`), G-08, G-15, §8.5. | none |

### 2.3 XML emission, TODOs, assets

| ID | Class | Reason / fix | P1 impact |
|---|---|---|---|
| REQ-REV-OUT-1 Canonical identity | **ADOPT-AMENDED** | Real bugs confirmed on `p0-p1`: (a) case-insensitive collision: `d1/Same.oef` and `d2/same.oef` produce `Same.xml` and `same.xml`, which overwrite each other on Windows/macOS (the dedup `seen` dict is case-sensitive); (b) two inputs with the same stem get `x.xml` and `x_2.xml` but **both have `id="x"`**; (c) stale `<stem>.xml` is not removed when a later run gives `echec` for that file (see RUN-3). Fix: casefold the collision key, derive `@id` from the final unique stem, report `source→sortie`. Not adopted: default tree-preserving layout (would change REQ-OUT-1 and the pipeline convention `ID_CODEX_v1.xml`); `--collision-policy` is unnecessary when the deterministic suffix exists; "validate root @id for schema compatibility" is vacuous (RNG: `data type="string"`). | small |
| REQ-REV-OUT-2 Complete TODO manifest | **ADOPT-AMENDED** | Valid inconsistency: REQ-TODO-1 caps the fragment at 4000 characters (plus SHA-256 of the full text) while REQ-TODO-6 and AC-8 speak of the verbatim fragment with a hash check. Codex implies a platform limit; the 4000 is the spec's own choice. Measured on `p0-p1` over the 1438 files: **21 of 30,647 placeholders** hit the cap (21 files). `placeholder_lint` only hash-checks fragments `< 4000`. Recommended amendment: keep the XML self-contained by splitting an over-long fragment into numbered placeholders (`part k/N`, each ≤ 4000, full SHA-256 on part 1) and lint the reassembled text; add an **optional** `--todos-json` sidecar for tooling. Do not make the sidecar authoritative: it can be separated from the XML, while the XML is what gets imported. The "dependency chain / affected questions" fields are extra. | small (emit + lint) |
| REQ-REV-OUT-3 Placeholder survivability | **ADOPT-AMENDED** (merge with OUT-2) | R10/Q5 already state that carrier survival is unverified, mitigated by the switchable carrier and the TODO list repeated on the `info` icon. Valid: until Q5, an optional sidecar is a backup. The import/export retention test is P3 and needs the platform. The "missing or modified placeholder is a validation failure" is already REQ-TODO-6 for the converter's own output. | none beyond OUT-2 |
| REQ-REV-OUT-4 HTML and media safety | **ADOPT-AMENDED** | (1) Naming clash: Codex's `strict` (allowlist) is not the spec's `--html strict` (every HTML fragment → G-17). Making the spec's `strict` the default would turn essentially all statements `partiel` (`html:div` 1208, `span` 166, `p` 62 occurrences on the corpus) and break §14.2. Keep `pass` as default. (2) Adopt an **always-gap list, regardless of mode**: `<script> <form> <input>` (G-19, already done), plus `on*=` attributes, `javascript:`/`vbscript:`/`data:text/html` URLs, `<style> <link> <meta> <base>`, `<object> <embed>`, and `<iframe>` (owner decides the YouTube case: 12 Gn files). (3) Reject `--html unsafe-pass`: there is no reason to offer a flag to emit `<script>`, and it depends on `publication`. (4) "No network downloads" is already REQ-ARCH-3/§7.6; asset path traversal/symlink checks belong to `--assets-dir` (P2). | small (tag-regex list) |
| REQ-REV-OUT-5 XML parser hardening | **ADOPT-AMENDED** (low) | The converter's only XML inputs are its own output and the local schemas (OEF text is escaped by the emitter). Risk is low, but a `_parser()` helper (`resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False`) in `validate.py` is cheap. "Maximum nesting depth and processing duration" is over-specification. The Codex §8.6 fix to `validation/xml/tests/run_schema_tests.py` is not allowed (see §6). | small |
| REQ-REV-OUT-6 Schema provenance | **ADOPT-AMENDED** | Cheap and deterministic: record the file name + SHA-256 of each schema and the profile (`v1`). Do **not** record absolute paths (determinism, AC-6). `source_format_original="oef"` belongs in the report only. Status vocabulary: the spec has `ok/ko/non_execute` (REQ-REP-5); add `non_fourni` for "Schematron not supplied". Keep French keys. | small |

### 2.4 Processes, batching, determinism, reports

| ID | Class | Reason / fix | P1 impact |
|---|---|---|---|
| REQ-REV-RUN-1 Safe compiler invocation | **ADOPT-AMENDED** | Already: argument array, no shell (REQ-WIN-3), scratch copy and cleanup (REQ-ARCH-4). `p0-p1` already has a hard-coded 60 s timeout, but a timeout becomes a generic "compiler refused/timeout" `echec`. Adopt: `--gate-timeout`, a distinct `compilateur: timeout` value, compiler SHA-256 in the report. Reject CPU/memory/output limits (hard on Windows, no evidence of need for a syntax-only compiler) and "referenced resources unavailable in scratch mode": `oef2wims` is a syntax compiler and reads no referenced files. | small |
| REQ-REV-RUN-2 Gate honesty | **ADOPT-AMENDED** | **Real defect on `p0-p1`** (`pipeline.py`): in `validator` mode `compilateur` is set to `ok`/`ko`, so a run with no compiler present reports `compilateur: ok`. The default `--gate auto` silently falls back. Amend REQ-REP-5: `compilateur` only for the real compiler; the fallback goes to a separate `validateur` field and `compilateur: non_execute`; add a `gate` field naming the mode used; define `statut` under `--gate none/validator` (REQ-REP-3 requires "compile gate OK"). "Cannot produce `publication=APPROVED`": drop (REL-2). | small |
| REQ-REV-RUN-3 Atomic outputs | **ADOPT-AMENDED** | Per-file write to a temp name + `os.replace`, and remove or flag a stale `<stem>.xml` when the file is `echec` (confirmed missing in `cli.py`). "Stage the whole batch then rename" is unnecessary for a one-shot tool. `--force` already only lifts the input-folder guard; the sources are `.oef`, outputs `.xml`. | small |
| REQ-REV-RUN-4 Deterministic core vs runtime metadata | **ADOPT-AMENDED** | REQ-OUT-3/AC-6 already require byte-identical output. Fix the wording: "for the same input bytes + options + tool/schema versions", `--stamp` excluded, report `source` relative to the input root (today it stores the path as passed). A separate `run-manifest.json` is YAGNI: the tool emits no mutable data today. | none |
| REQ-REV-RUN-5 Machine-readable diagnostics | **ADOPT-AMENDED** (trimmed) | REQ-REP-2 `details[]` already has `niveau`, `ligne_oef`, `colonne_oef`, `construct`, `regle`, `message`; those cover Codex's severity, span, rule_id and code. Adopt only `version_rapport` (the report has none; Codex's "2 proposed" presupposes a v1 that was never defined) and `questions_affectees`. Reject `recovery`, `evidence_level`, per-detail `source_sha256`, and the English keys (`code`, `severity`, `rule_id`…) that contradict Codex's own "preserve French keys" rule. | small |
| REQ-REV-RUN-6 Confidentiality / `--redact-report` | **REJECT** | REQ-ARCH-3 already forbids network and LLM use. The report contains no source fragments (they live in the XML placeholders), so there is nothing to redact, and the XML itself contains the solutions. | none |

### 2.5 Delivery modes, publication

| ID | Class | Reason / fix | P1 impact |
|---|---|---|---|
| REQ-REV-REL-1 Explicit modes | **REJECT** (P1/P2) / DEFER `verify` to P3 | `publish-check` needs a real import into the target platform, which §3.2 puts out of scope (importing, authentication, uploading) and Q5 cannot supply. `inspect` ≈ `--dump-ir`, `convert` = the CLI. Re-slicing the CLI into modes breaks §12.1, AC-12 and the existing `p0-p1` CLI. | **rework if adopted** |
| REQ-REV-REL-2 `publication` tri-state | **REJECT** | Until D-02/Q5 it would be a constant `BLOCKED`. It duplicates the existing axes (`fidelite: non_verifiee`, plus `risque_evaluation` from SEM-2), and the "teacher remediation workflow" is out of scope. If you want a visible signal now, `risque_evaluation` + `fidelite` is enough. | **rework if adopted** |
| REQ-REV-REL-3 Version-pinned evidence | **DEFER** (P3/P4) | Sensible for a release process. Cheap subset for the gate reports now: converter commit, Python/`lxml` versions, schema and compiler SHA-256. | none |
| REQ-REV-REL-4 Acceptance independence | **COVERED** | §14.2 "Rules that apply to every corpus (hard, no threshold)", AC-8, REQ-REP-7, R11. Optional one-line addition: "§14.2 shares are coverage KPIs, not quality evidence". | none |

---

## 3. Codex's 10 acceptance criteria

| ID | Class | Reason / fix | Phase |
|---|---|---|---|
| AC-REV-01 dispositions + spans + SHA | **COVERED** | AC-7 and REQ-REP-4 (I1–I3, with the independent XML scan). Spans/hashes follow the amended IN-1. | P1 |
| AC-REV-02 no path collision / overwrite / partial output / asset escape | **ADOPT-AMENDED** | Overlaps AC-11 (Unicode, no write beside input). Adopt the new parts: casefold collisions, unique `@id`, no stale/partial output (confirmed defects). Asset escape is P2. The "Windows/Linux adversarial suite" needs the ShadowPC; the Linux part can run now. | P1 |
| AC-REV-03 full TODO manifests, unreachable orphans | **ADOPT-AMENDED** | Rewrite for the multi-part / optional sidecar design of OUT-2. Importer round trip is P3. REQ-TODO-6 already tests unreachability. | P1 |
| AC-REV-04 no executable HTML / external entities | **ADOPT-AMENDED** | Replace "executable HTML" with the always-gap list of OUT-4 and test it with fixtures in `tests/`. | P1 |
| AC-REV-05 bounded, recorded, isolated compiler calls | **ADOPT-AMENDED** | Timeout and distinct code; failure injection can reuse `validation/oef/oef2wims/tests/fake_validator.py` without modifying it. "Missing dependency" does not apply to `oef2wims`. | P0/P1 |
| AC-REV-06 byte-identical XML/report/manifests | **COVERED** | AC-6, with the wording fix of RUN-4. | P1 |
| AC-REV-07 no `APPROVED` without real import | **REJECT** | Depends on REL-2; vacuous without it. | – |
| AC-REV-08 0 critical errors; ≥ 90% presentation pass | **ADOPT-AMENDED** | Stricter than B3's "≥ 24 of 30 pass C1–C6", and sensible, but "presentation" needs defining. C1 (statement faithful) is semantic, not presentation. Proposal: C1–C4 and C6 = critical (0 failures allowed), C5 = 100%, plus a new C7 (typography/layout) ≥ 90%. Rewrite AC-10 accordingly. Codex's factual slip: it says the current gate lets 6 of 30 fail "C1–C5", but the gate is C1–C6 and C6 (invented logic) is already a hard 0. | P3 |
| AC-REV-09 mapping records for all M-nn | **DEFER** | Fixtures per `M-nn` are already in §13.4; reviewer evidence is process. | P2/P3 |
| AC-REV-10 reference checker | **ADOPT** | Correct and in P0 (`tools/` is outside `validation/`). Note: use a reference-only mutation (a whole-token rename passes, as I verified), keep the existing Q-removal assertion, and add a test that the script finds the spec from any working directory. | P0 |

---

## 4. Other sections of Codex's document

### 4.1 §1 audit table (14 rows)

| Row | Class | Note |
|---|---|---|
| §4.4/§8.4/AC-8 complet vs grading | ADOPT-AMENDED | see SEM-4 |
| §6.3 M-48 / HTML | ADOPT-AMENDED | see OUT-4 |
| §13/§14 schema-valid ≠ importable; "independent publication gate" | COVERED (first half) / REJECT (gate) | §2.3 item 3, REQ-SCH-6, R1 say it. The gate needs the platform (Q5). The "C1–C5" is a slip, see AC-REV-08. |
| §4.1/§11.2 compiler | ADOPT-AMENDED | RUN-1 |
| REQ-TODO-1/6 4000 chars | ADOPT-AMENDED | OUT-2; the spec is explicit about the cap, so "requires verbatim complete" is a tension, not a flat contradiction |
| §12.2 `<stem>.xml` collisions | ADOPT-AMENDED | OUT-1; the exact refs are REQ-OUT-1 and REQ-BATCH-2 |
| REQ-IN-3 | ADOPT-AMENDED | IN-2 |
| REQ-EXPR-4 | ADOPT-AMENDED | SEM-5 |
| §13.3 N3/N7 | ADOPT-AMENDED / DEFER (P3) | N3 renames `\x2oN` and `\x2orepN` into one `\x2o1, \x2o2…` sequence, so the kind is lost: use separate counters. N7 "collapse whitespace" must exempt `<pre>`, code and TeX token boundaries. |
| "byte-identical report" vs `--stamp`, paths | ADOPT-AMENDED | RUN-4 |
| `--validate none` / `--gate none` | ADOPT-AMENDED | RUN-2 (the existing `non_execute` already lists skipped gates, but the validator-fallback label lies) |
| §17 Q1/Q5 "machine-readable blocker register" | REJECT | duplicates the Q table (§17.1); D-01…D-08 map to Q1, Q5, Q6, Q8, Q5, (new), Q2, (new). Only D-06 (approved HTML subset / image URI policy) and D-08 (licence of redistributed compiler binaries; the repo has none) are new. The `OPEN/DECIDED/VERIFIED` status machinery is overhead. |
| `check_refs.py` | ADOPT | verified, see §1 |
| README/lock/CI/provenance | DEFER mostly | `pyproject.toml` already on `p0-p1`; README is a P0 deliverable; lockfile, ruff/mypy, Windows CI, release provenance are optional (P2–P4) |

### 4.2 §2 goals, §4 report contract, §5 protocol, §6 roadmap, §9 definition of done

| Item | Class | Note |
|---|---|---|
| §2 "four independent axes" | ADOPT-AMENDED | coverage = `statut`, structural = `rng/xsd/shape`, semantic evidence = `fidelite`. The fourth axis (deployment readiness) conflicts with §3.2 and REL-2: reject it. Rewriting §1.2 is not needed; add one sentence "`complet` ≠ safe to publish". |
| §1 "non-negotiable preservation rules" | COVERED | REQ-TODO-2/3, §3.2, §2.3, REQ-REP-3/7, §2.2 |
| §4 report example | ADOPT-AMENDED | keep `statut/fidelite`; drop `publication`, `evidence` object (duplicates `compilateur/rng/xsd/schematron`) and `gaps_manifest`; mixed-language keys |
| §4 "JSON and TSV" | **ADOPT** | correct: §1.2 item 4 and §4.4 title say CSV while the option writes TSV (`--csv FILE.tsv`) |
| §5.1 test pyramid | COVERED (mostly) | levels 1–5, 7 restate §13.1–13.4/B3. New and fine: metamorphic tests (path renaming, encoding invariance, fuzzed nesting; `validation/…/fuzz_oracle.py` exists) → DEFER (P2). Level 6 (target runtime) = T2/T3, conditional on a platform |
| §5.2 N3 / N7 / N9 | ADOPT-AMENDED, DEFER (P3) | N9 ("normalisation never changes ordered answer types, solution strings, options, embed associations") is a good clarification of N8; "DIFF-EXPLAINED must cite a detail with a span" matches the existing definition |
| §5.5 thresholds caveat | COVERED | §14.2 caveat and the "> bound unexplained" rule |
| §6 roadmap vs §15 | see §5 | |
| §9 Definition of done | ADOPT-AMENDED | keep as an informative sentence ("converter MVP" vs "production-ready after platform verification"). Drop `APPROVED`. |

### 4.3 Codex §8 targeted repository fixes

| # | Class | Note |
|---|---|---|
| 1 `check_refs.py` | ADOPT | see §1 |
| 2 carrier contradiction | ADOPT (amended: decide `text` now) | see §1 |
| 3 Status line "Nothing … has been implemented" | **ADOPT** | line 10 is stale now that the validation tooling exists; reword after P1 merges |
| 4 §1.3 / Appendix C stale | **ADOPT** | confirmed stale: §1.3 "three commits", "README 9 bytes", line 88 "no converter code yet", C.1 "all under `/workspace/oef2xml/`" and "(v0.2)" (lines 1289, 1293), C.2 line 1318 and C.3 row 1 "no LICENSE" |
| 5 JSON/CSV → TSV; `report.schema.json` | ADOPT / DEFER | schema + golden fixtures in P2 |
| 6 hardened parser + extra fixtures in `validation/xml/tests/run_schema_tests.py` | **REJECT as located** | `validation/` must stay as is (REQ-ARCH-5, owner rule). Put the hardened parser in `src/oef2xml/validate.py` and any new fixtures (entities, depth, unknown block type accepted by RNG/XSD but caught by shape lint) in top-level `tests/`. The "RNG accepts an unknown type, shape lint must catch it" test is good and belongs to P1 (REQ-VAL-3, AC-5). |
| 7 README | ADOPT | P0 deliverable (on `p0-p1` it is only a heading so far) |
| 8 build metadata | DEFER mostly | see §4.1 |

---

## 5. Roadmap: Codex §6 vs spec §15

| Phase | Codex | Spec §15 | Assessment |
|---|---|---|---|
| P0 | split P0a (spec + audit + threat model) / P0b (IR JSON schema, registries, report v2 schema, compiler adapter, differential samples) | foundations: parser, catalogue, CLI skeleton, report writer, gate wrapper; exit AC-1/2/3/13 | P0b is a different, heavier P0 than the one built (`af634a7`); IR JSON schema and registries conflict with the REJECTed SEM-1. Keep §15 P0; fold the spec fixes into v0.2.6. |
| P1 | MVP + sanitized HTML, full-fidelity TODO manifest, taint on scoring settings, atomic outputs, collision-safe paths; exit = MVP gate + AC-REV-01–04, 06 | MVP gate §14.2 + AC-5…AC-8, AC-11, AC-12 | The additions are small hardening items (§6 below), not a different P1. Keep the P1 gate as is; add AC-REV-02/04/05 (amended) as extra checks. Do not make AC-REV-03 depend on an importer. |
| P2 | lists/matrices, expressions, six `wims()` subcommands, selected CAS, trig **only with verified units**, AC-REV-09 | lists, matrix (Q13), function/evalue/diff, `wims()` six, pari/maxima patterns, correspond/reorder/menu, **HTML handling, images/assets, idiom recognition**, trig behind `--trig-units` | Codex silently drops correspond/reorder/menu, assets, idioms and HTML work from P2. "Verified units" would block trig for good (Q6 has no answer path); the spec's opt-in `--trig-units` is the right design. |
| P3 | target runtime adapter, grading oracle, RT-A/B/C, audited teacher sample, publication checks; AC-REV-07/08 | `\condition`/`\feedback`, static steps, `\solution`/`\hint` (Q10), RT-A/B/C, E-O; AC-9/10 | Codex's P3 **deletes the feature work** (feedback, steps) that §15 puts in P3. Its runtime adapter is conditional on Q5. As a replacement it is incomplete; as an addition (verification track) it is fine. |
| P4 | PyInstaller, web UI, gap visualisation, guided manual remediation, XML schema upgrade | flydraw primitives, PyInstaller, minimal page | "Guided remediation" and a UI beyond the minimal page are scope creep (§3.2). Schema upgrade is the owner's, not this tool's. |

Net: do not replace §15. Keep it and bolt on the hardening items below.

---

## 6. What affects the P1 work running on `p0-p1`

No requirement invalidates the existing parser, ids, expression handling, mappings, emitter or report. The delta, if the amended items are adopted, is all small and additive:

| Area | Needed change | Where |
|---|---|---|
| Output naming | casefold collision key; `@id` from the final unique stem; atomic write; stale-output handling for `echec` | `cli.py` (+ `pipeline.py` for `id`) |
| Gate honesty | `compilateur` only for the real compiler; `validateur` + `gate` fields; `--gate-timeout`, `timeout` value; compiler SHA-256 | `pipeline.py`, `gate.py`, `report.py`, TSV columns |
| TODO fidelity | multi-part placeholder (or sidecar) for fragments ≥ 4000 characters; lint on reassembled text | `emit.py`, `validate.py` (`placeholder_lint` currently hash-checks only `< 4000`) |
| HTML | always-gap list: `on*=`, `javascript:`/`data:text/html`, `<iframe>`, `<object>/<embed>`, `<style>/<link>/<meta>/<base>` | `textparse.py` |
| Report | `source_sha256`, size, EOL profile, `version_rapport`, `risque_evaluation`, schema hashes; `source` relative to the input root | `report.py`, `pipeline.py` |
| Hardened lxml parser | `_parser()` helper | `validate.py` |

These would **rework** P1 if adopted as written: SEM-1 (per-node IR provenance), REL-1 (modes), REL-2 / AC-REV-07 (`publication`), RUN-5 in full (English keys), IN-3 as a "no regex" rule.
Items that **change gate numbers**: a default `--html strict` (OUT-4 as Codex names it) or demoting `\precision`/`weight=` files to `partiel` (SEM-4) would move §14.2 bounds and thresholds. Neither should be done in v0.2.6.
Items that **must not touch `validation/`**: Codex §8.6 (see §4.3).
Side note found on `p0-p1` (not Codex's): `mapping.yaml` / `expr_spec.json` from REQ-ARCH-2 / REQ-EXPR-1 are not present (ids and tables are in code). That is a spec-vs-code gap for P2, independent of this review.

---

## 7. Codex factual accuracy

| Codex statement | Check |
|---|---|
| "1,348-line v0.2.5" | **Wrong by one**: 1,347 lines (`wc -l` and `grep -c ''` on `origin/main`). |
| baseline commit `fdeb2b8d246af7699ea3b72b546f15299f51ab80` | Correct. |
| 121 H / 212 M / 1,100 Gn, 1,433 non-test files, 5 eligible MVP files | Correct (§2.2, §14.2). |
| `check_refs.py` default path and `or True` | Correct (lines 5 and 44). But its "make missing definitions fail" is already true. |
| changelog says `display_element`, §6.5 says `text` | Correct (line 41). |
| REQ-TODO-1/6 "4,000 characters" vs "verbatim fragment" | Correct tension. The cap is a spec choice, not a platform limit. |
| G-19 covers `<script>`, `<form>`, `<input>` | Correct, and M-48 contradicts it (Codex notes the combination but not the M-48 contradiction). |
| manual gate "lets 6 of 30 fail C1–C5" | **Inaccurate**: C1–C6, and C6 is a hard 0 already. |
| §12.1 `--placeholder-carrier` default `text` | Correct. |
| README "only a heading" | Correct on `main` (9 bytes). |
| "the tool should read JSON and TSV" | Correct. |
| `R-REV-` identifiers announced | None is defined anywhere in the document. |
| `report_schema_version: 2` | There is no v1; the spec's report has no version field. |
| `AC-REV-nn` identifiers | `check_refs.py` matches `AC-(\d+)` only, so these would not be cross-checked. `REQ-REV-*-n` would match. |
| "Review status: not executed, figures retained" | Honest. Codex did not count anything itself, so none of its numbers are independent. |
| missed by Codex | `acos` absent from `math_trig`; WIMS aliases; B.2 lacks the inverse forward idiom; M-48 vs G-19; REQ-REP-3 "nothing lost" vs M-07/G-05. |

---

## 8. Recommended change list

### v0.2.6 (spec + tools; no code behaviour change except where marked)

1. `tools/corpus_stats/check_refs.py`: default `parents[2]/docs/CAHIER_DES_CHARGES_OEF2XML.md`; replace the `or True` check by a real one; negative controls (reference-only mutation, missing Q, run from another cwd) in `tests/`.
2. Changelog line 41: carrier is `text` by default and switchable (`display_element` kept as option).
3. M-48 / G-19 / §12.1: one rule. Always G-19 (any mode): `<script> <form> <input>`, `on*=`, `javascript:`/`vbscript:`/`data:text/html` URLs, `<style> <link> <meta> <base> <object> <embed>`; `<iframe>` pending your decision (12 Gn files with YouTube embeds). Default `--html pass` unchanged; spec's `--html strict` unchanged. Record the measured G-19 frequency (0 files for script/form/input/on*/javascript; 12 iframe).
4. REQ-EXPR-4 / G-21 / B.2: add the direct/inverse table of §1; `acos` always a gap (no `ACOS` in `math_trig`); alias list; inverse forward idiom `asin(x)*180/pi`.
5. REQ-REP-3 vs M-07/G-05: reword `complet`; add per-question `risque_evaluation` (statut unchanged). Owner decision: should dropping `\precision`/`weight=` demote to `partiel` (requires recomputing `scope_bounds.py`)?
6. REQ-TODO-1/6 + AC-8: resolve cap vs verbatim: numbered multi-part placeholders (+ optional `--todos-json`); lint on the reassembled fragment.
7. REQ-OUT-1 / REQ-BATCH-2: casefold collisions, deterministic suffix, unique `@id`, atomic write, stale-output rule; report maps `source→sortie`.
8. REQ-ARCH-4 / REQ-REP-5 / §12.1: gate honesty (`gate`, `compilateur` = real compiler only, `validateur`), `--gate-timeout`, distinct `timeout`; compiler SHA-256 in the report.
9. REQ-IN-3: write down the decoding order (strict UTF-8 → strict cp1252 → latin-1) and `encodage_ambiguite` when bytes 0x80–0x9F appear (2 of 267 files).
10. Hygiene: status line, §1.3, C.1/C.2/C.3 row 1 stale items, "JSON and TSV" (§1.2.4, §4.4), AC-6 wording ("same input bytes + options + versions"; `--stamp` excluded; relative `source`), `version_rapport`, per-file `source_sha256`/size/EOL and schema SHA-256 in the report, N3 with separate `\x2oN`/`\x2orepN` counters, N7 `<pre>` exception, N9 sentence.

### v0.3 (after P1 merges)

- AC-10 rewrite with severity classes (C1–C4, C6 critical; C5 100%; new C7 presentation ≥ 90%) = Codex AC-REV-08.
- SEM-3 mapping records / AC-REV-09 together with `mapping.yaml` (REQ-ARCH-2) in P2.
- SEM-6 and the Q5 sub-question "is `random_number` inclusive at both ends?"; REL-3 release manifest; `report.schema.json`; metamorphic tests; CI (Linux first, Windows when the PC is online).
- Decisions for you: HTML allowlist and iframe policy (Codex D-06); redistribution/licence of compiler binaries if they are ever bundled (D-08).

### Do not adopt

SEM-1 (as written), RUN-6, REL-1, REL-2, AC-REV-07, the decision-register machinery (D-xx statuses), Codex's replacement roadmap, any edit to `validation/` (Codex §8.6), `--html unsafe-pass`.

---

## 9. Counts

Codex's 38 normative ids (28 `REQ-REV-*` + 10 `AC-REV-*`):

| Class | REQ-REV (28) | AC-REV (10) | Total (38) |
|---|---:|---:|---:|
| ADOPT | 0 | 1 (AC-REV-10) | **1** |
| ADOPT-AMENDED | 16 (IN-1, IN-2, SEM-2, SEM-4, SEM-5, OUT-1…6, RUN-1…5) | 5 (02, 03, 04, 05, 08) | **21** |
| ALREADY-COVERED | 5 (IN-3, IN-4, IN-5, SEM-7, REL-4) | 2 (01, 06) | **7** |
| REJECT | 4 (SEM-1, RUN-6, REL-1, REL-2) | 1 (07) | **5** |
| DEFER | 3 (SEM-3, SEM-6, REL-3) | 1 (09) | **4** |
| **Total** | 28 | 10 | **38** |

Of the 21 ADOPT-AMENDED, about 16 are P1-relevant small hardening items (IN-1, SEM-2, SEM-4, OUT-1, OUT-2, OUT-3, OUT-4, OUT-6, RUN-1, RUN-2, RUN-3, RUN-5, plus AC-REV-02…05). The rest are doc wording or P3.
Secondary items (audit table, §8 fixes, other sections, decisions): about 3 ADOPT (`check_refs`, TSV title, stale status/§1.3), most others ADOPT-AMENDED or COVERED, 3 REJECT (D-register, hardened tests inside `validation/`, replacement roadmap), a handful DEFER.
