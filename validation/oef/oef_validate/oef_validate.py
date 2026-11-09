#!/usr/bin/env python3
"""Validateur statique de fichiers OEF (WIMS), Python 3, bibliothèque standard uniquement.

Il reproduit l'analyse faite par le compilateur oef2wims (src/OefMsg2wims/oef2wims.c,
oeflines.c, process.c, outexec.c de WIMS) puis ajoute des contrôles de cohérence.

Usage : python oef_validate.py [--spec oef_spec.json] [--strict] fichier.oef [dossier ...]
Sortie : fichier:ligne:colonne: niveau: message   (niveau = erreur | avertissement)
Code de sortie : 1 si au moins une erreur (ou un avertissement avec --strict), sinon 0.
"""
import argparse, json, os, re, sys

ELSE, ENDIF, NEXT, WHILE = '\x01', '\x02', '\x03', '\x04'
CTRL = {ELSE: 'else', ENDIF: 'endif', NEXT: 'next', WHILE: 'endwhile'}
NON_VAR_DEFS = {'credits', 'mdef'}          # t_def à 2 arguments qui ne déclarent pas de variable
RESERVED = re.compile(r'^(reply\d*|reply_\w*|result\d*|choice\d*|step\d*|sc_reply\d*|sc_choice\d*|'
                      r'imagedir|confparm[1-4]|oefenv|empty|exit|help_subject|status|m_\w*|wims_\w*)$')
TEXT_DIRECTIVES = {'statement', 'hint', 'help', 'solution'}  # passés à out_exec() ; \latex exclu (code LaTeX)

class Issue:
    def __init__(self, level, pos, msg): self.level, self.pos, self.msg = level, pos, msg

class Validator:
    def __init__(self, spec):
        self.spec = spec
        self.dirs = spec['directives']
        self.lim = spec['limits']
        self.alias = spec['anstype_aliases']
        self.scripts = spec['anstype_scripts']
        self.glob_opts = set(spec.get('global_reply_options', {}))
        self.text_cmds = set(spec.get('text_commands', {}))

    # --- primitives identiques à src/Lib/liblines.c -------------------------
    @staticmethod
    def find_matching(b, i, c):
        """find_matching() : i pointe après la parenthèse ouvrante. Renvoie l'index ou None."""
        par = brk = brc = 0; n = len(b)
        while i < n:
            ch = b[i]
            if ch == '[': brk += 1
            elif ch == ']': brk -= 1
            elif ch == '(': par += 1
            elif ch == ')': par -= 1
            elif ch == '{': brc += 1
            elif ch == '}': brc -= 1
            else: i += 1; continue
            if par < 0 or brk < 0 or brc < 0:
                if ch != c or par > 0 or brk > 0 or brc > 0: return None
                return i
            i += 1
        return None

    @staticmethod
    def ws(b, i):
        while i < len(b) and b[i] in ' \t\n\r\f\v': i += 1
        return i

    # --- vérification forte des parenthèses (oeflines.c: checkparentheses) ---
    def check_parentheses(self, b):
        self.badpar = None
        n = len(b); i = 0
        pairs = {'(': ')', '[': ']', '{': '}'}
        while i < n:
            ch = b[i]
            if ch in ')]}': return i, ch
            if ch in pairs:
                pe = self.find_matching2(b, i + 1, pairs[ch])
                if pe is None:
                    bp = self.badpar if self.badpar is not None else i
                    return bp, b[bp]
                i = pe
            i += 1
        return None

    def find_matching2(self, b, i, c):
        par = brk = brc = 0; ppar = pbrk = pbrc = None; n = len(b)
        while i < n:
            ch = b[i]
            if ch == '[':
                if brk == 0: pbrk = i
                brk += 1
            elif ch == ']': brk -= 1
            elif ch == '(':
                if par == 0: ppar = i
                par += 1
            elif ch == ')': par -= 1
            elif ch == '{':
                if brc == 0: pbrc = i
                brc += 1
            elif ch == '}': brc -= 1
            else: i += 1; continue
            if par < 0 or brk < 0 or brc < 0:
                if self.badpar is None:
                    if par > 0: self.badpar = ppar
                    if brc > 0: self.badpar = pbrc
                    if brk > 0: self.badpar = pbrk
                if par > 0 or brk > 0 or brc > 0: return None
                if ch != c:
                    if self.badpar is None: self.badpar = i
                    return None
                return i
            i += 1
        return None

    # --- analyse principale ---------------------------------------------------
    def validate(self, path):
        issues = []
        def add(level, pos, msg): issues.append(Issue(level, pos, msg))
        raw = open(path, 'rb').read()
        try: text = raw.decode('utf-8')
        except UnicodeDecodeError: text = raw.decode('latin-1')
        self.text = text
        if len(raw) == 0:
            add('erreur', 0, 'fichier vide (oef2wims : "Empty source file.")'); return issues
        if len(raw) >= self.lim['MAX_FLEN']:
            add('erreur', 0, 'fichier trop long : %d octets, limite %d (oef2wims : "Source file bad or too long.")' % (len(raw), self.lim['MAX_FLEN']))
            return issues
        # getinp() : \r et caractères 0..6 remplacés par des espaces
        b = [(' ' if (c == '\r' or ord(c) <= 6) else c) for c in text]
        bad = self.check_parentheses(b)
        if bad:
            add('erreur', bad[0], "parenthèse/crochet/accolade non appariée '%s' (oef2wims : \"Unmatched parentheses\"). "
                "Le compilateur compte (), [] et {} dans tout le fichier, texte compris, sans échappement." % bad[1])
            return issues
        defs = self.process(b, add)
        if defs is None: return issues
        self.checks(b, defs, add)
        return issues

    def process(self, b, add):
        """Réplique process() de oef2wims.c et renvoie la liste des directives trouvées."""
        defs = []; n = len(b); p = 0
        statement_seen = steps_seen = False
        while p < n and len(defs) < self.lim['MAX_DEFINE']:
            ch = b[p]
            if ch in CTRL:
                defs.append({'name': CTRL[ch], 'pos': p, 'args': [], 'post': statement_seen}); p += 1; continue
            if ch == '{':
                q = self.find_matching(b, p + 1, '}')
                if q is None: add('erreur', p, 'accolade non appariée'); return None
                p = q + 1; continue
            if ch != '\\': p += 1; continue
            start = p; p += 1; pe = p
            while pe < n and (b[pe].isalnum() and b[pe].isascii() or b[pe] == '_'): pe += 1
            pp = self.ws(b, pe)
            if pp >= n or b[pp] != '{':
                if pp > p: p = pp
                continue
            name = ''.join(b[p:pe])
            d = self.dirs.get(name)
            if d is None:
                q = self.find_matching(b, pp + 1, '}')
                if q is None: add('erreur', pp, 'accolade non appariée'); return None
                if name and self.is_toplevel_unknown(name):
                    add('avertissement', start, "commande \\%s inconnue d'oef2wims au niveau principal : ignorée silencieusement par le compilateur" % name)
                p = q + 1; continue
            args = []; j = 0; last_end = pe - 1
            while j < d['maxargs']:
                if j > 0 and (pp >= n or b[pp] != '{'): break
                q = self.find_matching(b, pp + 1, '}')
                if q is None: add('erreur', pp, 'accolade non appariée'); return None
                args.append((pp + 1, q)); last_end = q; pp = self.ws(b, q + 1); j += 1
            rec = {'name': name, 'pos': start, 'args': args, 'post': statement_seen,
                   'vals': [''.join(b[s:e]) for s, e in args]}
            kind = d['kind']
            if kind == 't_main':
                if statement_seen: add('erreur', start, '\\statement défini plusieurs fois (oef2wims : "Multiple definition of statement.")')
                statement_seen = True
            if kind == 't_step':
                if steps_seen: add('erreur', start, '\\steps ou \\nextstep défini plusieurs fois (oef2wims : "Multiple definition of steps.")')
                steps_seen = True
            if kind == 't_def' and d['maxargs'] < 2 and d['maxargs'] == 1 and args:
                # \if{..}{..}{..}, \ifval, \for, \while : le corps est analysé en ligne
                pt = self.ws(b, last_end + 1); pt3 = None
                if pt < n and b[pt] == '{':
                    b[pt] = ' '; pt2 = self.find_matching(b, pt, '}')
                    if pt2 is None: add('erreur', pt, 'accolade non appariée'); return None
                    pt3 = self.ws(b, pt2 + 1)
                else:
                    pt2 = pt
                    add('avertissement', start, '\\%s{...} sans bloc {...} qui le suit' % name)
                if pt2 < n:
                    if name in ('if', 'ifval'):
                        if pt3 is not None and pt3 < n and b[pt3] == '{':
                            b[pt2] = ELSE; b[pt3] = ' '
                            pt2 = self.find_matching(b, pt3, '}')
                            if pt2 is None: add('erreur', pt3, 'accolade non appariée'); return None
                        b[pt2] = ENDIF
                    elif name == 'while': b[pt2] = WHILE
                    else: b[pt2] = NEXT
            else:
                # arguments en trop : le compilateur les saute comme blocs anonymes
                if pp < n and b[pp] == '{' and d['maxargs'] > 0 and kind not in ('t_head', 't_head2', 't_lang', 't_tit'):
                    add('avertissement', pp, '\\%s accepte au plus %d argument(s) : le bloc {...} suivant est ignoré' % (name, d['maxargs']))
            defs.append(rec)
            p = last_end + 1 if args else pe
        if p < n and len(defs) >= self.lim['MAX_DEFINE']:
            add('erreur', p, 'plus de %d directives : oef2wims ignore la suite du fichier (MAX_DEFINE)' % self.lim['MAX_DEFINE'])
        if not statement_seen:
            add('erreur', 0, 'aucun \\statement (oef2wims : "No statement defined.")')
        return defs

    def is_toplevel_unknown(self, name):
        return not (name in self.text_cmds or RESERVED.match(name))

    # --- contrôles complémentaires -------------------------------------------
    def checks(self, b, defs, add):
        L = self.lim
        declared = {}            # nom -> position de déclaration
        # variables de boucle de \for (au niveau principal ou dans les textes, cf. outexec.c exec_for)
        for m in re.finditer(r'\\for\s*\{\s*([A-Za-z_]\w*)\s*(=|in\b)', self.text):
            declared.setdefault(m.group(1), m.start())
        answers = 0; choices = 0
        for d in defs:
            name = d['name']; kind = self.dirs.get(name, {}).get('kind')
            vals = d.get('vals', [])
            if kind == 't_tit' and vals and len(vals[0].strip()) > L['MAX_TITLEN']:
                add('avertissement', d['pos'], 'titre de %d caractères : tronqué à %d par oef2wims' % (len(vals[0].strip()), L['MAX_TITLEN']))
            if kind == 't_def' and self.dirs[name]['maxargs'] == 2 and name not in NON_VAR_DEFS:
                v0 = vals[0] if vals else ''
                v1 = vals[1] if len(vals) > 1 else ''
                if v1 == '' and '=' in v0:
                    var = v0.split('=', 1)[0]
                    if var.endswith(':'): var = var[:-1]
                else:
                    var = v0
                    if v1 == '' and len(vals) < 2:
                        add('avertissement', d['pos'], "\\%s{%s} sans '=' ni second argument : variable sans valeur" % (name, v0.strip()[:30]))
                var = var.strip()
                # oef2wims retire un '\' initial du nom (def.c:104 : if(*p[0]=='\\') p[0]++;)
                if var.startswith('\\'): var = var[1:]
                if not re.fullmatch(r'[A-Za-z_]\w*(\[[^\]]*\])?', var):
                    add('avertissement', d['pos'], "nom de variable inhabituel dans \\%s : '%s'" % (name, var[:40]))
                else:
                    var = var.split('[')[0]
                    if len(var) >= L['MAX_NAMELEN']: add('erreur', d['pos'], 'nom de variable trop long (>= %d)' % L['MAX_NAMELEN'])
                    if name in ('real', 'integer', 'int', 'rational', 'complex', 'function', 'matrix', 'text', 'parameter', 'variable'):
                        self.check_refs(d, declared, add, start_arg=0 if v1 == '' else 1, skip_name=True)
                    declared.setdefault(var, d['pos'])
            elif name == 'for' and vals:
                m = re.match(r'\s*([A-Za-z_]\w*)\s*(=|in\b)', vals[0])
                if m: declared.setdefault(m.group(1), d['pos'])
                else: add('erreur', d['pos'], "\\for{...} doit commencer par 'variable=' ou 'variable in' (ex. \\for{i=1 to 5}, \\for{x in \\liste})")
            elif kind == 't_ans':
                answers += 1
                # réponse « analysée » : \answer{..}{\nom;...} avec \nom non déclaré (process.c:299-322)
                if len(vals) > 1:
                    m = re.match(r'\s*\\([A-Za-z0-9_]+)\s*(;|$)', vals[1])
                    if m and m.group(1) not in declared: declared[m.group(1)] = d['pos']
                self.check_answer(d, add, declared)
            elif kind == 't_choi':
                choices += 1
                if len(vals) < 3: add('avertissement', d['pos'], '\\choice attend {intitulé}{bonne(s) réponse(s)}{mauvaises réponses} : %d argument(s) trouvé(s)' % len(vals))
            elif name in TEXT_DIRECTIVES or name == 'feedback':
                self.check_text(d, declared, add, args=[1] if name == 'feedback' else [0])
        self.answers, self.choices = answers, choices
        # \embed{reply n} / \embed{rn} / \embed{choice n}
        for m in re.finditer(r'\\embed\s*\{\s*(reply|r|choice|c)\s*(\d+)', self.text):
            k = int(m.group(2)); is_choice = m.group(1) in ('choice', 'c')
            total = choices if is_choice else answers
            if k < 1 or k > total:
                add('erreur', m.start(), '\\embed{%s %d} mais l\'exercice ne définit que %d %s' % (m.group(1), k, total, '\\choice' if is_choice else '\\answer'))

    def check_answer(self, d, add, declared):
        vals = list(d['vals'])
        typ = None; opts = []; positional = []
        for v in vals:
            s = v.lstrip()
            m = re.match(r'(?i)type\s*=', s)
            mo = re.match(r'(?i)options?\s*=', s)
            mw = re.match(r'(?i)weight\s*=', s)
            if m: typ = s[m.end():].split()[0] if s[m.end():].split() else ''
            elif mo:
                body = re.sub(r'"[^"]*"|\[[^\]]*\]|\([^)]*\)', ' ', s[mo.end():])
                for tok in re.split(r'[\s,;]+', body.strip()):
                    if re.match(r'[A-Za-z_]', tok): opts.append(tok)
            elif mw: pass
            else: positional.append(v)
        if len(positional) < 2:
            add('avertissement', d['pos'], '\\%s : intitulé ou bonne réponse manquant(e) (%d argument(s) positionnel(s))' % (d['name'], len(positional)))
        if positional:
            prompt = ' '.join(positional[0].split())
            if '\\' not in prompt and len(prompt) >= self.lim['MAX_PROMPTLEN']:
                add('erreur', d['pos'], 'intitulé de réponse de %d caractères : oef2wims refuse >= %d ("Answer prompt too long")' % (len(prompt), self.lim['MAX_PROMPTLEN']))
            elif '\\' in prompt and len(prompt) >= self.lim['MAX_PROMPTLEN']:
                add('avertissement', d['pos'], 'intitulé de réponse long (%d car.) : après substitution des variables il doit rester < %d caractères' % (len(prompt), self.lim['MAX_PROMPTLEN']))
        script = None
        if typ is None:
            script = 'default'
        elif typ == '':
            # oef2wims accepte et écrit replytypeN= vide (process.c p_answer) : pas un refus du compilateur,
            # mais la réponse n'aura pas de type à l'exécution -> avertissement fort
            add('avertissement', d['pos'], 'type= vide dans \\%s : accepté par oef2wims (replytype vide) mais la réponse n\'aura aucun type à l\'exécution' % d['name'])
        elif typ.startswith('\\'):
            pass  # type calculé par une variable
        elif typ in self.alias: script = self.alias[typ]['script']
        elif typ in self.scripts and self.scripts[typ]['has_input']: script = typ
        else:
            add('avertissement', d['pos'], "type de réponse '%s' inconnu des sources WIMS : accepté seulement si le module fournit son propre anstype" % typ)
        if script and opts:
            known = set(self.scripts.get(script, {}).get('options', {})) | self.glob_opts
            for o in opts:
                w = o.split('=')[0]
                if not w or w.startswith('\\') or w in known: continue
                add('avertissement', d['pos'], "option '%s' non lue par l'anstype '%s' d'après les sources (vérifier l'orthographe)" % (w, script))

    def check_refs(self, d, declared, add, start_arg=0, skip_name=False):
        for idx, (s, e) in enumerate(d['args']):
            if idx < start_arg: continue
            seg = self.text[s:e]
            if skip_name and idx == 0 and '=' in seg:
                off = seg.index('=') + 1; seg = seg[off:]; s += off
            for m in re.finditer(r'(?<!\\)\\([A-Za-z]\w*)', seg):
                nm = m.group(1)
                if nm in declared or RESERVED.match(nm) or nm in self.dirs: continue
                if self.later_declared(nm):
                    add('avertissement', s + m.start(), '\\%s utilisée avant sa déclaration' % nm)

    def later_declared(self, nm):
        return re.search(r'\\(real|integer|int|rational|complex|function|matrix|text|parameter|variable)\s*\{\s*%s\s*:?=' % re.escape(nm), self.text) is not None

    def check_text(self, d, declared, add, args):
        """Dans les textes (out_exec), un \\nom non déclaré hors \\( \\) devient $m_nom : vide à l'exécution."""
        for idx in args:
            if idx >= len(d['args']): continue
            s, e = d['args'][idx]; t = self.text; i = s
            while i < e:
                if t[i] != '\\': i += 1; continue
                c = t[i + 1] if i + 1 < e else ''
                if c == '\\': i += 2; continue
                if c in '({':
                    close = ')' if c == '(' else '}'
                    p2 = self.find_matching(t, i + 2, close)
                    p3 = t.find('\\' + close, i, e)
                    if p3 != -1 and (p2 is None or p3 < p2): p2 = p3 + 1
                    if p2 is None: i += 2; continue
                    i = p2 + 1; continue
                m = re.match(r'[A-Za-z]\w*', t[i + 1:e])
                if not m: i += 1; continue
                nm = m.group(0)
                if nm in self.text_cmds:
                    # \embed{...}, \special{...}, \draw{..}{..} : contenu transmis tel quel (outexec.c _matchit*)
                    q = self.ws(t, i + 1 + len(nm))
                    while q < e and t[q] == '{':
                        r = self.find_matching(t, q + 1, '}')
                        if r is None: break
                        q = self.ws(t, r + 1)
                    i = q; continue
                if (nm in declared or RESERVED.match(nm) or nm in self.text_cmds or nm in self.dirs
                        or nm in ('for', 'if', 'ifval', 'exit')):
                    i += 1 + len(nm); continue
                if self.later_declared(nm):
                    if not d['post']:
                        pass  # déclarée après \statement : valeur calculée après soumission (postdef)
                else:
                    add('avertissement', i, "\\%s n'est ni une variable déclarée ni une commande OEF : hors de \\( \\) elle sera remplacée par une valeur vide" % nm)
                i += 1 + len(nm)

def line_col(text, pos):
    line = text.count('\n', 0, pos) + 1
    col = pos - (text.rfind('\n', 0, pos) + 1) + 1
    return line, col

def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for dp, dn, fns in os.walk(p):
                dn.sort()
                for f in sorted(fns):
                    if f.lower().endswith('.oef'): yield os.path.join(dp, f)
        else:
            yield p

def main(argv=None):
    ap = argparse.ArgumentParser(description='Validateur de fichiers OEF (WIMS)')
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--spec', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'oef_spec.json'))
    ap.add_argument('--strict', action='store_true', help='les avertissements font aussi échouer')
    ap.add_argument('-q', '--quiet', action='store_true', help="n'afficher que le résumé")
    ap.add_argument('--no-warnings', action='store_true', help='masquer les avertissements')
    a = ap.parse_args(argv)
    with open(a.spec, encoding='utf-8') as f: spec = json.load(f)
    v = Validator(spec)
    nfiles = nerr_files = nwarn_files = 0; failed = False
    for path in iter_files(a.paths):
        nfiles += 1
        try: issues = v.validate(path)
        except OSError as e:
            print('%s:0:0: erreur: lecture impossible (%s)' % (path, e)); failed = True; nerr_files += 1; continue
        errs = [i for i in issues if i.level == 'erreur']
        warns = [i for i in issues if i.level != 'erreur']
        if errs: nerr_files += 1
        if warns: nwarn_files += 1
        if errs or (a.strict and warns): failed = True
        if not a.quiet:
            for i in sorted(issues, key=lambda x: x.pos):
                if a.no_warnings and i.level != 'erreur': continue
                l, c = line_col(v.text if hasattr(v, 'text') else '', i.pos)
                print('%s:%d:%d: %s: %s' % (path, l, c, i.level, i.msg))
    print('Résumé : %d fichier(s), %d avec erreur(s), %d avec avertissement(s), %d sans erreur'
          % (nfiles, nerr_files, nwarn_files, nfiles - nerr_files), file=sys.stderr)
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
