import subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(HERE, '..', 'oef_validate.py')

def test_variable_declaree_avec_backslash(tmp_path):
    f = tmp_path / 'b.oef'
    f.write_text('\\title{t}\n\\text{\\estconstante=est une constante}\n\\statement{a \\estconstante b}\n')
    r = subprocess.run([sys.executable, V, str(f)], capture_output=True, text=True)
    assert r.returncode == 0
    assert 'estconstante' not in r.stdout

def test_type_vide_est_avertissement(tmp_path):
    f = tmp_path / 't.oef'
    f.write_text('\\title{t}\n\\integer{n=2}\n\\statement{\\embed{reply1}}\n\\answer{}{\\n}{type=}\n')
    r = subprocess.run([sys.executable, V, str(f)], capture_output=True, text=True)
    assert r.returncode == 0 and 'type= vide' in r.stdout
