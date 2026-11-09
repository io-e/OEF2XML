#!/usr/bin/env python3
"""Génère oef_spec.json à partir des sources WIMS (stdlib uniquement).

Usage : python gen_spec.py /chemin/vers/wims [-o oef_spec.json]
Sources lues :
  src/OefMsg2wims/oef2wims.c   table directives[] (nom, type, nb d'arguments)
  src/OefMsg2wims/process.c    table anstype[] (alias -> fichier anstype)
  src/OefMsg2wims/sp.c         table specialfn[] (fonctions spéciales)
  src/OefMsg2wims/outexec.c    commandes traitées dans les textes (\\embed, \\special, ...)
  public_html/scripts/anstype/ mots d'option lus dans $(replyoption$i)
  public_html/scripts/oef/     options globales lues dans replyoption
"""
import json, os, re, sys, argparse

def rel(root, p):
    return os.path.relpath(p, root).replace(os.sep, '/')

def read(p):
    with open(p, encoding='latin-1') as f:
        return f.read()

def line_of(text, pos):
    return text.count('\n', 0, pos) + 1

def table(root, path, start_re, entry_re):
    full = os.path.join(root, path); t = read(full)
    m = re.search(start_re, t)
    if not m: raise SystemExit('table introuvable dans ' + path)
    end = t.index('};', m.end())
    out = []
    for e in re.finditer(entry_re, t[m.end():end]):
        out.append((e, line_of(t, m.end() + e.start())))
    return out

OPT_PATTERNS = [
    r'([A-Za-z_][\w]*)\s+(?:iswordof|notwordof|isin|notin|isitemof|notitemof)\s+\$\(?{v}',
    r'!getopt\s+([A-Za-z_]\w*)\s+in\s+\$\(?{v}',
]

def options_in(text, varnames):
    found = {}
    for v in varnames:
        vv = re.escape(v)
        for pat in OPT_PATTERNS:
            for m in re.finditer(pat.format(v=vv), text):
                w = m.group(1)
                if w in ('i', 'j', 'k', 'n'): continue
                found.setdefault(w, line_of(text, m.start()))
    return found

def aliases(text):
    names = ['replyoption$i', 'replyoption$j', 'replyoption$k', 'replyoption$n', 'replyoption$(i)']
    for m in re.finditer(r'^\s*(?:!set\s+|!default\s+)?([A-Za-z_]\w*)\s*=\s*(?:!trim\s+|!words2items\s+)?\$\(replyoption\$i\)\s*$', text, re.M):
        names.append(m.group(1))
    for m in re.finditer(r'^\s*(?:!set\s+)?([A-Za-z_]\w*)\s*=\s*\$\(?replyoption\$i\)?\s*$', text, re.M):
        names.append(m.group(1))
    return names

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('wims_root'); ap.add_argument('-o', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oef_spec.json'))
    a = ap.parse_args(); root = a.wims_root
    spec = {'generated_from': os.path.abspath(root), 'wims_version': read(os.path.join(root, 'version')).strip() if os.path.exists(os.path.join(root, 'version')) else None}
    oefc = 'src/OefMsg2wims/oef2wims.c'
    for name in ('MAX_TITLEN', 'MAX_PARM', 'MAX_PARAM', 'MAX_DEFINE', 'MAX_FLEN'):
        m = re.search(r'#define\s+%s\s+(\d+)' % name, read(os.path.join(root, oefc)))
        spec.setdefault('limits', {})[name] = int(m.group(1)) if m else None
    for hdr, names in (('src/OefMsg2wims/oef2wims.h', ('MAX_PROMPTLEN',)), ('src/wimsdef.h', ('MAX_LINELEN', 'MAX_NAMELEN'))):
        t = read(os.path.join(root, hdr))
        for name in names:
            m = re.search(r'#define\s+%s\s+(\d+)' % name, t)
            spec['limits'][name] = int(m.group(1)) if m else None
            if m: spec.setdefault('limits_source', {})[name] = '%s:%d' % (hdr, line_of(t, m.start()))
    dirs = {}
    for e, ln in table(root, oefc, r'directives\[\]\s*=\s*\{', r'\{"(\w+)",\s*(t_\w+),\s*(\d+),\s*(\w+)\}'):
        dirs[e.group(1)] = {'kind': e.group(2), 'maxargs': int(e.group(3)), 'processor': e.group(4), 'source': '%s:%d' % (oefc, ln)}
    spec['directives'] = dirs
    pc = 'src/OefMsg2wims/process.c'
    ans = {}
    for e, ln in table(root, pc, r'anstype\[\]\s*=\s*\{', r'\{"(\w+)",\s*(typ_\w+),\s*"(\w+)"\}'):
        ans[e.group(1)] = {'typ': e.group(2), 'script': e.group(3), 'source': '%s:%d' % (pc, ln)}
    spec['anstype_aliases'] = ans
    spc = 'src/OefMsg2wims/sp.c'
    spec['special_functions'] = {e.group(1): '%s:%d' % (spc, ln) for e, ln in table(root, spc, r'specialfn\[\]\s*=\s*\{', r'\{"(\w+)",\s*(\w+)\}')}
    oe = 'src/OefMsg2wims/outexec.c'; t = read(os.path.join(root, oe))
    spec['text_commands'] = {m.group(1): '%s:%d' % (oe, line_of(t, m.start())) for m in re.finditer(r'_matchit\d\(&p, &ps, "(\w+)"', t)}
    adir = os.path.join(root, 'public_html/scripts/anstype')
    scripts = {}
    for fn in sorted(os.listdir(adir)):
        if '.' in fn or fn.startswith('_'): continue
        opts = {}
        files = [g for g in sorted(os.listdir(adir)) if g == fn or g.startswith(fn + '.') or g.startswith(fn + '_')]
        texts = {g: read(os.path.join(adir, g)) for g in files}
        # fichiers partagés lus par l'anstype (!read anstype/xxx ou !read xxx.inc)
        for t in list(texts.values()):
            for m in re.finditer(r'anstype/([\w.]+)', t):
                g = m.group(1)
                if g not in texts and os.path.isfile(os.path.join(adir, g)):
                    texts[g] = read(os.path.join(adir, g))
        al = sorted({x for t in texts.values() for x in aliases(t)})
        for g, t in texts.items():
            for w, ln in options_in(t, al).items():
                opts.setdefault(w, '%s:%d' % (rel(root, os.path.join(adir, g)), ln))
        # en-tête documentaire « option: ... » des fichiers anstype
        for g, t in texts.items():
            for ln, line in enumerate(t.split('\n')[:6], 1):
                if line.startswith('option:'):
                    body = re.sub(r'"[^"]*"|\[[^\]]*\]', ' ', line[len('option:'):])
                    for w in re.findall(r'([A-Za-z_]\w*)\s*=?', body):
                        if w in ('or', 'and', 'no', 'list', 'of', 'some', 'atoms'): continue
                        opts.setdefault(w, '%s:%d' % (rel(root, os.path.join(adir, g)), ln))
        scripts[fn] = {'has_input': os.path.exists(os.path.join(adir, fn + '.input')), 'options': opts}
    spec['anstype_scripts'] = scripts
    odir = os.path.join(root, 'public_html/scripts/oef'); glob = {}
    for dp, dn, fns in os.walk(odir):
        for fn in fns:
            p = os.path.join(dp, fn)
            try: t = read(p)
            except Exception: continue
            for w, ln in options_in(t, aliases(t)).items():
                glob.setdefault(w, '%s:%d' % (rel(root, p), ln))
    spec['global_reply_options'] = dict(sorted(glob.items()))
    with open(a.o, 'w', encoding='utf-8') as f:
        json.dump(spec, f, ensure_ascii=False, indent=1, sort_keys=False)
    print('écrit', a.o, ':', len(dirs), 'directives,', len(ans), 'alias anstype,', len(scripts), 'scripts anstype')

if __name__ == '__main__':
    main()
