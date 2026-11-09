# Eleda schema test fixtures (v1)

Fixtures for the OEF2XML specification (section 13.1, REQ-SCH-7, REQ-LANG-1, REQ-TODO-1).

| Fixture | Expected | What it proves |
|---|---|---|
| `valid/minimal_info_chain.xml` | valid (RNG + XSD) | `info` -> `variables_set` -> `display_element` chain; an **orphan top-level `text` block** carrying a TODO **comment icon** (same attributes as the 2085 real icons: `text pinned height width`); `<lang>` with an **empty `<description/>`** |
| `invalid/source_format_oef.xml` | invalid | `source_format="oef"` is not in `json|yaml|ir|xml` (SC-1) |
| `invalid/lang_ca.xml` | invalid | `lang/@code="ca"` is not in `fr en es it de ar` (SC-2) |
| `invalid/lang_missing_description.xml` | invalid | `<lang>` without `<description>` (it is required) |

All four files differ only in the attribute/element under test.

Run (needs Python 3 and `lxml`):

    python3 run_schema_tests.py        # add -v to print the schema error of each expected failure

Validates each file against `../schemas_v1/eleda_program_v1.rng` and `.xsd`. Exit code 0 only if `valid/` passes and `invalid/` fails in **both** schemas; 1 otherwise; 2 on setup error.
