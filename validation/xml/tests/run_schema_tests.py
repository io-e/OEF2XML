#!/usr/bin/env python3
"""Schema fixture runner for the Eleda program schemas v1 (OEF2XML spec, section 13.1).

Validates every fixture against ../schemas_v1/eleda_program_v1.rng AND ../schemas_v1/eleda_program_v1.xsd with lxml.
  valid/*.xml    must PASS  both schemas
  invalid/*.xml  must FAIL  both schemas
Exit code 0 only if every expectation holds in both schemas; 1 otherwise; 2 on setup error.
Usage: python3 run_schema_tests.py [--schemas DIR] [-v]
"""
import argparse, sys
from pathlib import Path
from lxml import etree

here = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--schemas', default=str(here.parent / 'schemas_v1'))
ap.add_argument('-v', '--verbose', action='store_true', help='print the first schema error of each expected failure')
a = ap.parse_args()
sd = Path(a.schemas)
try:
    rng = etree.RelaxNG(etree.parse(str(sd / 'eleda_program_v1.rng')))
    xsd = etree.XMLSchema(etree.parse(str(sd / 'eleda_program_v1.xsd')))
except (OSError, etree.LxmlError) as e:
    print('setup error:', e); sys.exit(2)

def check(validator, doc):
    ok = validator.validate(doc)
    err = '' if ok else str(validator.error_log.last_error)
    return ok, err

bad = 0; n = 0
for kind, expect in (('valid', True), ('invalid', False)):
    files = sorted((here / kind).glob('*.xml'))
    if not files:
        print(f'ERROR no fixture in {kind}/'); bad += 1
    for f in files:
        try: doc = etree.parse(str(f))
        except etree.XMLSyntaxError as e:
            print(f'FAIL {kind}/{f.name}: not well-formed: {e}'); bad += 1; continue
        for name, v in (('rng', rng), ('xsd', xsd)):
            n += 1
            ok, err = check(v, doc)
            status = 'PASS' if ok == expect else 'FAIL'
            if ok != expect: bad += 1
            line = f'{status} {kind}/{f.name} [{name}] -> {"valid" if ok else "invalid"} (expected {"valid" if expect else "invalid"})'
            if (a.verbose or ok != expect) and err: line += f'\n       {err}'
            print(line)
print(f'{n - bad}/{n} expectations met' if bad == 0 else f'{bad} of {n} expectations NOT met')
sys.exit(1 if bad else 0)
