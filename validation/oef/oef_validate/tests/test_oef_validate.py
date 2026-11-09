import json, os, subprocess, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import oef_validate as ov

SPEC = json.load(open(os.path.join(ROOT, 'oef_spec.json'), encoding='utf-8'))

def run(name):
    v = ov.Validator(SPEC)
    issues = v.validate(os.path.join(HERE, 'samples', name))
    return [(i.level, ov.line_col(v.text, i.pos), i.msg) for i in issues]

def errors(name):
    return [x for x in run(name) if x[0] == 'erreur']

def test_minimal_ok():
    assert run('ok_minimal.oef') == []

def test_no_statement():
    e = errors('no_statement.oef')
    assert len(e) == 1 and 'aucun \\statement' in e[0][2]

def test_double_statement():
    e = errors('double_statement.oef')
    assert any('plusieurs fois' in m for _, _, m in e)
    assert e[0][1] == (2, 1)

def test_unclosed_brace_position():
    e = errors('unclosed_brace.oef')
    assert len(e) == 1 and 'non appariée' in e[0][2]
    assert e[0][1] == (2, 11)   # même position que oef2wims (ligne 2 colonne 11)

def test_paren_in_text_is_error():
    # oef2wims compte aussi les ( ) du texte : "1)" casse la compilation
    assert errors('paren_in_text.oef')

def test_embed_reply_out_of_range():
    e = errors('embed_too_many.oef')
    assert any('\\embed{reply 2}' in m for _, _, m in e)

def test_prompt_too_long():
    assert any('Answer prompt too long' in m for _, _, m in errors('prompt_too_long.oef'))

def test_warnings_only():
    r = run('warnings.oef')
    assert not [x for x in r if x[0] == 'erreur']
    msgs = ' '.join(m for _, _, m in r)
    assert "'nombre'" in msgs and '\\inconnue' in msgs

def test_double_steps():
    assert any('steps' in m for _, _, m in errors('double_steps.oef'))

def test_empty():
    assert any('vide' in m for _, _, m in errors('empty.oef'))

def test_cli_exit_codes():
    py = sys.executable; cli = os.path.join(ROOT, 'oef_validate.py')
    ok = subprocess.run([py, cli, os.path.join(HERE, 'samples', 'ok_minimal.oef')], capture_output=True, text=True)
    ko = subprocess.run([py, cli, os.path.join(HERE, 'samples', 'no_statement.oef')], capture_output=True, text=True)
    assert ok.returncode == 0 and ko.returncode == 1
    assert ko.stdout.split(':')[1:3] == ['1', '1']
    w = subprocess.run([py, cli, '--strict', os.path.join(HERE, 'samples', 'warnings.oef')], capture_output=True, text=True)
    assert w.returncode == 1
