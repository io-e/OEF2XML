#requires -Version 7.0
<#
.SYNOPSIS
    Validates Eleda programme XML files with the Blockly DTD/XSD and Eleda RNG/Schematron.
.DESCRIPTION
    Uses the Eleda programme DTD/XSD plus the existing Eleda programme RNG/Schematron.
    Writes one adjacent <XML-basename>_.check log per XML, a CSV report, and a
    console summary. Requires Python with lxml.
.PARAMETER Path
    Directory containing XML files (recursively) or a single XML file.
.PARAMETER Report
    Optional CSV report path. Defaults to Validation_AllSchemas.csv in Path's directory.
.EXAMPLE
    .\Test-ProgramsXml-AllSchemas.ps1 'D:\ALF_ZGit\41-eleda_education\programs_xml_v1'
#>
[CmdletBinding()]
param(
    [Parameter(Position=0)]
    [string]$Path = 'D:\ALF_ZGit\41-eleda_education\programs_xml_v1',
    [string]$Report = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$SchemaDir = $PSScriptRoot
$DtdPath = Join-Path $SchemaDir 'ELEDA_program_v2.dtd'
$XsdPath = Join-Path $SchemaDir 'ELEDA_program_v2.xsd'
$RngPath = Join-Path $SchemaDir 'ELEDA_program_v2.rng'
$SchPath = Join-Path $SchemaDir 'ELEDA_program_v2.sch'

if (-not (Test-Path -LiteralPath $Path)) { throw "Input path not found: $Path" }
foreach ($schema in @($DtdPath,$XsdPath,$RngPath,$SchPath)) {
    if (-not (Test-Path -LiteralPath $schema)) { throw "Schema not found: $schema" }
}
$Python = (Get-Command python -ErrorAction Stop).Source
$item = Get-Item -LiteralPath $Path
$files = if ($item.PSIsContainer) {
    @(Get-ChildItem -LiteralPath $item.FullName -Filter '*.xml' -File -Recurse | ForEach-Object FullName)
} else { @($item.FullName) }
if ($files.Count -eq 0) { throw "No XML files found under: $Path" }
if (-not $Report) {
    $reportDir = if ($item.PSIsContainer) { $item.FullName } else { $item.DirectoryName }
    $Report = Join-Path $reportDir 'Validation_AllSchemas.csv'
}

$py = @'
import csv, sys
from pathlib import Path
from lxml import etree
from lxml.isoschematron import Schematron

dtd_path, xsd_path, rng_path, sch_path, report_path, list_path = sys.argv[1:]
with open(list_path, encoding="utf-8") as f:
    files = [line.rstrip("\r\n") for line in f if line.rstrip("\r\n")]
dtd = etree.DTD(dtd_path)
xsd = etree.XMLSchema(etree.parse(xsd_path))
rng = etree.RelaxNG(etree.parse(rng_path))
sch = Schematron(etree.parse(sch_path), store_report=True)

def valid(schema, doc):
    ok = schema.validate(doc)
    if ok:
        return "PASS", ""
    return "FAIL", " | ".join(str(e).strip() for e in schema.error_log[:5])

def validate_schematron(doc):
    if sch.validate(doc):
        return "PASS", ""
    ns={"svrl":"http://purl.oclc.org/dsdl/svrl"}
    report=sch.validation_report
    failed=report.findall(".//svrl:failed-assert",ns) if report is not None else []
    errors=[a for a in failed if a.get("role")=="error"]
    messages=[]
    for a in failed[:8]:
        node=a.find("svrl:text",ns)
        msg=(node.text or "").strip().splitlines()[0] if node is not None else "Schematron assertion failed"
        messages.append(f"[{a.get('role','warn')}] {msg}")
    return ("FAIL" if errors else "WARN"), " | ".join(messages)

results=[]
for fp in files:
    row={"file":fp}
    try:
        doc=etree.parse(fp)
        root=doc.getroot()
        row["DTD"], row["DTD_details"] = valid(dtd,doc)
        row["XSD"], row["XSD_details"] = valid(xsd,doc)
        row["RNG"], row["RNG_details"] = valid(rng,doc)
        row["SCH"], row["SCH_details"] = validate_schematron(doc)
    except Exception as e:
        for name in ("DTD","XSD","RNG","SCH"):
            row[name], row[name+"_details"] = "ERROR", str(e)
    results.append(row)
    # Keep an individual, human-readable validation log beside its XML input.
    check_path = Path(fp).with_name(Path(fp).stem + "_.check")
    with open(check_path, "w", encoding="utf-8") as log:
        log.write(f"File: {fp}\n")
        for name in ("DTD","XSD","RNG","SCH"):
            log.write(f"{name}: {row.get(name, 'ERROR')}\n")
            details = row.get(name+"_details", "")
            if details:
                log.write(f"  {details}\n")

fields=["file","DTD","DTD_details","XSD","XSD_details","RNG","RNG_details","SCH","SCH_details"]
with open(report_path,"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(results)
print(f"Files checked: {len(results)}")
for name in ("DTD","XSD","RNG","SCH"):
    passed=sum(r.get(name)=="PASS" for r in results)
    failed=sum(r.get(name)=="FAIL" for r in results)
    errors=sum(r.get(name)=="ERROR" for r in results)
    warned=sum(r.get(name)=="WARN" for r in results)
    print(f"{name}: {passed} PASS, {warned} WARN, {failed} FAIL, {errors} ERROR")
print(f"CSV report: {report_path}")
print(f"Per-file .check logs: {len(results)} (beside each XML)")
sys.exit(1 if any(r.get(n) not in ("PASS","WARN") for r in results for n in ("DTD","XSD","RNG","SCH")) else 0)
'@

$pyFile = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString() + '.py')
$listFile = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString() + '.txt')
try {
    Set-Content -LiteralPath $pyFile -Value $py -Encoding utf8NoBOM
    Set-Content -LiteralPath $listFile -Value ($files -join "`n") -Encoding utf8NoBOM
    $args = @('-I',$pyFile,$DtdPath,$XsdPath,$RngPath,$SchPath,$Report,$listFile)
    & $Python @args
    exit $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $pyFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $listFile -Force -ErrorAction SilentlyContinue
}
