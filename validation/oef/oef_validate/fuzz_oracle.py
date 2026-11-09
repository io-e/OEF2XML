#!/usr/bin/env python3
"""Mutations aléatoires des .oef officiels, verdict comparé au vrai oef2wims.
Usage : fuzz_oracle.py /chemin/oef2wims /chemin/wims [n]"""
import os, random, subprocess, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oef_validate as ov
comp, root = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 500
random.seed(42)
files = sorted(os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if f.endswith('.oef'))
v = ov.Validator(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oef_spec.json'))))
agree = 0; dis = []
tmp = tempfile.mkdtemp()
for k in range(n):
    src = open(random.choice(files), 'rb').read()
    if not src: continue
    op = random.choice(['del', 'ins', 'dupstmt', 'nostmt'])
    b = bytearray(src)
    idx = [i for i, c in enumerate(b) if c in b'{}()[]']
    if op == 'del' and idx: del b[random.choice(idx)]
    elif op == 'ins': b.insert(random.randrange(len(b)), random.choice(b'{}()[]'))
    elif op == 'dupstmt': b += b'\n\\statement{x}\n'
    elif op == 'nostmt': b = bytearray(bytes(b).replace(b'\\statement', b'\\statemant'))
    p = os.path.join(tmp, 'm.oef'); open(p, 'wb').write(b)
    c = b'ERROR' in subprocess.run([comp, p, os.path.join(tmp, 'm.def')], capture_output=True).stdout
    issues = v.validate(p)
    # on ne compare que les erreurs que le compilateur sait détecter (pas \embed hors limites)
    e = any(i.level == 'erreur' and '\\embed' not in i.msg for i in issues)
    if c == e: agree += 1
    else: dis.append((op, c, e))
print('mutations=%d accord=%d desaccord=%d' % (n, agree, len(dis)), dis[:10])
