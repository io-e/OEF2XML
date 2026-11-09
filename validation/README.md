# Validation files (OEF and Eleda XML)

## `oef/oef_validate/`
Static OEF validator in Python 3 (standard library only). Its rules reproduce the WIMS 4.31b `oef2wims` compiler.
`python3 oef_validate.py exo.oef|folder [--strict] [-q]` exits with code 1 on error. See `README.md` in that folder.
`oef_spec.json` is generated from the WIMS sources by `gen_spec.py`. `tests/` holds the pytest tests and intentionally broken samples.

## `oef/oef2wims/`
Sources, tests and docs for the Windows `oef2wims-v2.exe` and `oef2wims-log.exe` wrappers (E2 build with Unicode-path support) around the unchanged WIMS 4.31b compiler. `SHA256SUMS_E2.txt` lists the expected hashes.
The binaries are not committed. Keep them on the local machine or attach them to a GitHub Release.

## `xml/schemas_v1/`
Relax NG and XSD schemas for Eleda program XML, `urn:eleda:program:v1` (CLAUDE_V1_1). The XSD was generated from the RNG with Trang.
Validate with: `xmllint --noout --relaxng eleda_program_v1.rng file.xml`
The v2 set (`ELEDA_program_v2.dtd/.xsd/.rng/.sch` and `ELEDA_program_v2_Test-ProgramsXml-AllSchemas.ps1`) lives in `D:\ALF_Scripts\00-Schemas\03-xml_IR` and still has to be added (`xml/schemas_v2/`).
`ELEDA_program_v2_Test-ProgramsXml-AllSchemas.ps1` (PowerShell 7 + Python `lxml`) validates a folder of XML against DTD, XSD, RNG and Schematron, writing a `_.check` log per file and `Validation_AllSchemas.csv`. It looks for the four `ELEDA_program_v2.*` files in its own folder, so copy it next to them.

## Licence
The repository is AGPL-3.0 (see `LICENSE`). `oef2wims` and the rules reproduced by `oef_validate` derive from WIMS (GPL v2 or later), which is compatible.
