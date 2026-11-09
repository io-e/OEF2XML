#!/usr/bin/env python3
"""Corpus statistics for the OEF2XML requirements specification.

Parses OEF files the way upstream oef2wims (WIMS 4.31b, src/OefMsg2wims/oef2wims.c,
function process()) does: only *top-level* directives are recognised, a directive
is "\\name{...}{...}" with brace/paren/bracket matching (Lib/liblines.c find_matching),
and the bodies of \\if/\\ifval/\\for/\\while are scanned as top-level too.

Usage:  python3 oef_corpus_stats.py [--corpus DIR] [--map corpus.map] [--out DIR]
Outputs: corpus_stats.json, corpus_stats.md, per_file.csv  (in --out)

Origin classes (from corpus.map, written when the corpus was assembled):
  generated   = file produced by the user's own xml2oef converter (/workspace/oef_out/oef)
  upstream_*  = files shipped in the WIMS 4.31b tarball (class sources, model scripts, modules)
  ours        = e1..e5 test files made for oef2wims testing (excluded from statistics)
"""
import argparse, csv, json, os, re, sys, collections
from collections import Counter, defaultdict

# --- directive table copied from oef2wims.c: name -> number of braces parameters
DIRECTIVES = {
 'answer':5,'author':1,'choice':5,'complex':2,'computeanswer':1,'condition':4,'conditions':1,
 'credits':2,'css':1,'description':1,'else':0,'email':1,'endif':0,'endwhile':0,'feedback':2,
 'for':1,'format':1,'function':2,'help':1,'hint':1,'if':1,'ifval':1,'int':2,'integer':2,
 'keywords':1,'language':1,'latex':1,'matrix':2,'mdef':2,'next':0,'nextstep':1,'observation':1,
 'parameter':2,'plot':3,'precision':1,'range':1,'rational':2,'real':2,'reply':5,'solution':1,
 'statement':1,'steps':1,'text':2,'title':1,'title_ca':1,'title_cn':1,'title_en':1,'title_es':1,
 'title_fr':1,'title_it':1,'title_nl':1,'title_si':1,'variable':2,'while':1,'wims':1}
DEFS = {'complex','function','int','integer','matrix','mdef','parameter','rational','real','text','variable'}
CONTROL = {'if','ifval','for','while'}
SPECIAL_FN = ['asis','canvasdraw','column','deriv','derivative','det','determinant','diff','draw',
 'drawtikz','evaluate','evalue','htmlmath','int','integral','integrate','item','items','mathexp_cut',
 'maxima','pari','pickone','position','positionof','randint','randitem','random','randomitem',
 'randomrow','randrow','row','rows','shuffle','simplify','slib','solve','teximg','texmath','wims','yacas']
ANSTYPES = ['algexp','aset','atext','case','checkbox','chemeq','chset','click','clickfill','code',
 'compose','coord','coordinates','corresp','correspond','default','dragfill','equation','expalg',
 'formal','fset','function','imgcomp','javacurve','link','litexp','mark','matrix','menu','nocase',
 'number','numeric','numexp','radio','range','ranges','raw','reorder','select','set','sigunits',
 'symtext','text','textcomp','unit','units','vector','wlist','wordcomp']

def match(s, i, close):
    """s[i] is the char AFTER the opening char. Return index of matching `close` or -1
    (same algorithm as find_matching in Lib/liblines.c)."""
    p=b=r=0
    n=len(s)
    while i<n:
        c=s[i]
        if c=='[': b+=1
        elif c==']': b-=1
        elif c=='(': p+=1
        elif c==')': p-=1
        elif c=='{': r+=1
        elif c=='}': r-=1
        else:
            i+=1; continue
        if p<0 or b<0 or r<0:
            if c!=close or p>0 or b>0 or r>0: return -1
            return i
        i+=1
    return -1

def skip_ws(s,i):
    while i<len(s) and s[i] in ' \t\n\r\f\v': i+=1
    return i

def parse(text):
    """Return list of (name, [params]) top-level directives, + parse error flag."""
    s=text
    out=[]; i=0; n=len(s); err=None
    transparent=set()
    while i<n:
        c=s[i]
        if c=='{':
            if i in transparent: i+=1; continue
            j=match(s,i+1,'}')
            if j<0: err='unmatched {'; break
            i=j+1; continue
        if c!='\\': i+=1; continue
        j=i+1
        while j<n and (s[j].isalnum() or s[j]=='_') and ord(s[j])<128: j+=1
        name=s[i+1:j]
        k=skip_ws(s,j)
        if k>=n or s[k]!='{':
            i=max(k,i+1); continue
        if name not in DIRECTIVES:
            e=match(s,k+1,'}')
            if e<0: err='unmatched {'; break
            i=e+1; continue
        cnt=DIRECTIVES[name]; params=[]; pe=k-1
        pp=k
        for _ in range(cnt):
            if params and (pp>=n or s[pp]!='{'): break
            e=match(s,pp+1,'}')
            if e<0: err='unmatched {'; break
            params.append(s[pp+1:e]); pe=e
            pp=skip_ws(s,e+1)
        if err: break
        if name in CONTROL:
            q=skip_ws(s,pe+1)
            if q<n and s[q]=='{':
                transparent.add(q)
                if name in ('if','ifval'):
                    e=match(s,q+1,'}')
                    if e>0:
                        q2=skip_ws(s,e+1)
                        if q2<n and s[q2]=='{': transparent.add(q2)
        out.append((name,params))
        i=pe+1
    return out,err

# Planned mapping class of each OEF answer type (see spec section 8): D=direct, A=approximate, G=gap (no Eleda block)
ANSMAP={}
for t in ('numeric','number','radio','checkbox','correspond','corresp','reorder'): ANSMAP[t]='D'
for t in ('(none:','default','case','nocase','atext','text','raw','chset','formal','algexp','expalg','numexp','function','equation',
          'litexp','symtext','menu','select','range','ranges'): ANSMAP[t]='A'
def ansclass(t):
    return ANSMAP.get(t,'G')

def decode(raw):
    enc='utf-8'
    try: t=raw.decode('utf-8')
    except UnicodeDecodeError:
        t=raw.decode('latin-1'); enc='latin-1'
    return t,enc

def split_answer_params(params):
    """Return (prompt, expected, options dict, positional-rest)."""
    opts={}
    pos=[]
    for p in params:
        m=re.match(r'\s*(type|option|options|weight)\s*=\s*(.*)',p,re.I|re.S)
        if m: opts[m.group(1).lower().rstrip('s') if m.group(1).lower()!='options' else 'option']=m.group(2).strip()
        else: pos.append(p)
    return pos,opts

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--corpus',default='/workspace/oefc/corpus')
    ap.add_argument('--map',default='/workspace/oefc/corpus.map')
    ap.add_argument('--out',default='/workspace/oef2xml')
    a=ap.parse_args()
    origin={}
    for l in open(a.map,encoding='utf-8'):
        f,_,p=l.rstrip('\n').partition('\t')
        if '/oef_out/' in p: o='generated'
        elif '/log/classes/' in p: o='upstream_class'
        elif '/scripts/model/' in p: o='upstream_model'
        elif '/modules/' in p: o='upstream_module'
        else: o='upstream_other'
        origin[f]=(o,p)
    files=sorted(f for f in os.listdir(a.corpus) if f.endswith('.oef'))
    G={'all_upstream':{}, 'generated':{}, 'upstream_handwritten':{}, 'upstream_models':{}}   # group -> metric -> Counter
    def grp(o): return 'generated' if o=='generated' else 'all_upstream'
    def C(g,m):
        return G[g].setdefault(m,Counter())
    nfiles=Counter(); rows=[]; parse_err=Counter()
    ndef=defaultdict(list); sizes=defaultdict(list)
    prof={}
    for f in files:
        if f not in origin: continue   # e1..e5: our own test files
        o,_p=origin[f]
        raw=open(os.path.join(a.corpus,f),'rb').read()
        text,enc=decode(raw)
        d,err=parse(text)
        groups=[grp(o)]+(['upstream_handwritten'] if o in ('upstream_class','upstream_module') else [])+(['upstream_models'] if o=='upstream_model' else [])
        for g in groups:
            nfiles[g]+=1
            if o!='generated' and g=='all_upstream': nfiles[o]+=1
            C(g,'encoding')[enc if not raw.startswith(b'\xef\xbb\xbf') else enc+'+BOM']+=1
            C(g,'crlf')['crlf' if b'\r\n' in raw else 'lf']+=1
            sizes[g].append(len(raw))
            if err: parse_err[g]+=1
            ndef[g].append(len(d))
            names=[n for n,_ in d]
            for n in set(names): C(g,'dir_files')[n]+=1
            for n in names: C(g,'dir_occ')[n]+=1
            has_stmt='statement' in names
            feats=set()
            # answers
            nans=0; nch=0
            for n,ps in d:
                if n in ('answer','reply'):
                    nans+=1
                    pos,opts=split_answer_params(ps)
                    t=opts.get('type','(none: default)').lower()
                    t=re.sub(r'\s+',' ',t)
                    C(g,'answer_type')[t]+=1
                    C(g,'answer_occ_by_class')[ansclass(t.split()[0] if t and not t.startswith('\\') else 'DYN')]+=1
                    tk=t.split()[0] if t else '?'
                    if tk.startswith('\\'): tk='DYNAMIC'
                    feats.add('ans:'+tk)
                    if 'option' in opts: C(g,'answer_option_tokens').update(re.split(r'[\s,;]+',opts['option'].strip()))
                    if 'weight' in opts: C(g,'answer_has_weight')['y']+=1
                    exp=pos[1] if len(pos)>1 else ''
                    if re.match(r'\s*\\[A-Za-z_]\w*\s*(;|$)',exp): C(g,'answer_expected_is_variable_ref')['y']+=1; 
                elif n=='choice':
                    nch+=1
                    pos,opts=split_answer_params(ps)
                    t=opts.get('type','(none: default)').lower()
                    C(g,'choice_type')[re.sub(r'\s+',' ',t)]+=1
                    if 'option' in opts: C(g,'choice_option_tokens').update(re.split(r'[\s,;]+',opts['option'].strip()))
                    feats.add('choice:'+('DYNAMIC' if t.startswith('\\') else t.split()[0]))
                elif n=='language':
                    C(g,'language')[ps[0].strip().lower()]+=1
                elif n.startswith('title_'):
                    C(g,'title_lang')[n[6:]]+=1
                elif n=='precision': C(g,'precision_values')[ps[0].strip()]+=1
                elif n=='computeanswer': C(g,'computeanswer_values')[ps[0].strip().lower()]+=1
                elif n=='format': C(g,'format_values')[ps[0].strip().lower()]+=1
                elif n=='range': C(g,'range_values')[ps[0].strip()]+=1
                elif n in DEFS:
                    # code lives in params; count special functions called there
                    code=' '.join(ps)
                    for fn in SPECIAL_FN:
                        c=len(re.findall(r'(?<![\w\\])'+fn+r'\s*\(',code))
                        if c: C(g,'fn_occ')[fn]+=c; feats.add('fn:'+fn)
                    for m in re.finditer(r'(?<![\w\\])slib\s*\(\s*([A-Za-z0-9_/]+)',code): C(g,'slib_modules')[m.group(1)]+=1
                    for m in re.finditer(r'(?<![\w\\])wims\s*\(\s*([A-Za-z0-9_]+)',code): C(g,'wims_cmds')[m.group(1)]+=1
                    for m in re.finditer(r'(?<![\w\\])(pari|maxima|yacas)\s*\(',code): C(g,'cas_calls')[m.group(1)]+=1
                    if re.search(r'\bshuffle\s*\(',code): pass
                    if n in ('int','integer') : C(g,'def_kind')['integer']+=1
                    else: C(g,'def_kind')[n]+=1
                    if n!='mdef':
                        pass
            for n in set(names): feats.add('dir:'+n)
            cls=[ansclass(x[4:]) for x in feats if x.startswith('ans:')]
            if cls:
                C(g,'answer_files_by_worst_class')['G' if 'G' in cls else ('A' if 'A' in cls else 'D')]+=1
            for x in feats:
                if x.startswith('ans:'): C(g,'answer_type_files')[x[4:]]+=1
                if x.startswith('choice:'): C(g,'choice_type_files')[x[7:]]+=1
                if x.startswith('fn:'): C(g,'fn_files')[x[3:]]+=1
            C(g,'answers_per_file')[nans]+=1; C(g,'choices_per_file')[nch]+=1
            C(g,'questions_per_file')[nans+nch]+=1
            if nans+nch==0: C(g,'flag')['no_answer_or_choice']+=1
            if not has_stmt: C(g,'flag')['no_statement']+=1
            # embed / special / reply refs in the whole text
            emb=re.findall(r'\\embed\s*\{([^}]*)\}',text)
            spc=re.findall(r'\\special\s*\{([^}]*)\}',text)
            C(g,'embed_occ')['total']+=len(emb); C(g,'special_occ')['total']+=len(spc)
            if emb: C(g,'embed_files')['files']+=1; feats.add('embed')
            if spc: C(g,'special_files')['files']+=1; feats.add('special')
            for e in emb:
                e=e.strip(); k='reply%d' if False else None
                e0=e.split(',')[0].strip()
                if re.fullmatch(r'reply\s*\d+',e0): C(g,'embed_arg')['replyN']+=1
                elif re.fullmatch(r'choice\s*\d+',e0): C(g,'embed_arg')['choiceN']+=1
                elif re.fullmatch(r'[rc]\d+',e0): C(g,'embed_arg')['rN/cN']+=1
                elif e.startswith('\\'): C(g,'embed_arg')['\\variable']+=1
                else: C(g,'embed_arg')['other']+=1
            for s_ in spc:
                w=re.match(r'\s*(\w+)',s_); C(g,'special_arg')[w.group(1) if w else '?']+=1
            # text-level features
            for key,rx in [('img_tag',r'<img\b'),('imagedir',r'\\imagedir'),('filedir',r'\\filedir'),
                           ('latex_inline_paren',r'\\\('),('latex_display_bracket',r'\\\['),
                           ('dollar_math','\\$[^$]+\\$'),('html_entity',r'&[a-z#0-9]+;'),
                           ('tex_cmds_texmath',r'\\texmath'),('anchor_or_link',r'<a\s'),('table_tag',r'<table'),
                           ('script_tag',r'<script'),('wimscenter',r'wimscenter'),('input_or_form',r'<input|<form')]:
                if re.search(rx,text): C(g,'text_feature_files')[key]+=1
            # \special / embed within def?  Variable use of reply/choice
            for key,rx in [('uses_\\reply_var',r'\\reply\d'),('uses_\\choice_var',r'\\choice\d'),('uses_\\sc_reply',r'\\sc_reply'),('uses_\\step',r'\\step\b')]:
                if re.search(rx,text): C(g,'text_feature_files')[key]+=1
            prof[(f,g)]=(g,o,feats,nans+nch,enc,len(d),len(raw))
            if g==grp(o): rows.append([f,o,enc,len(raw),len(d),nans,nch,';'.join(sorted(feats))])
    # --- coverage tier M1 = exactly the phase-1 (MVP) scope of the specification (section 15): share of files whose
    # EVERY feature is inside it.  The final-scope upper bounds (complet/partiel eligible) are computed by scope_bounds.py.
    DIR1={'title','language','author','email','keywords','description','credits','css','observation','computeanswer','precision','range','format',
          'integer','int','real','rational','text','statement','answer','reply','choice','if','ifval','for','while','else','endif','next','endwhile',
          'title_en','title_fr','title_es','title_it','title_ca','title_cn','title_nl','title_si'}
    ANS1={'(none:','default','numeric','number','case','nocase','atext','text','raw','chset','formal','algexp','expalg','numexp','function','equation','litexp','symtext','radio','checkbox'}
    FN1={'randint','random','shuffle','randitem','randomitem','pickone','item','items'}
    def tier_ok(feats,t):
        for x in feats:
            k,_,v=x.partition(':')
            if k=='dir' and v not in DIR1: return False
            if k in('ans','choice') and v.split()[0] not in ANS1 and not v.startswith('(none'): return False
            if k=='fn' and v not in FN1: return False
            if x in('special',): return False
        return True
    tiers={}
    for g in ('all_upstream','upstream_handwritten','upstream_models','generated'):
        fs=[v for v in prof.values() if v[0]==g]
        tiers[g]={'M1_mvp_scope':sum(1 for v in fs if tier_ok(v[2],0)),'total':len(fs)}
    def q(xs,p):
        xs=sorted(xs); return xs[min(len(xs)-1,int(p*len(xs)))] if xs else None
    res={'files':dict(nfiles),'parse_errors':dict(parse_err),'tier_M1_mvp_scope':tiers,
         'directives_per_file':{g:{'median':q(ndef[g],.5),'p90':q(ndef[g],.9),'p99':q(ndef[g],.99),'max':max(ndef[g])} for g in ndef},
         'bytes_per_file':{g:{'median':q(sizes[g],.5),'p90':q(sizes[g],.9),'max':max(sizes[g])} for g in sizes},
         'over_MAX_DEFINE_1024':{g:sum(1 for x in ndef[g] if x>1024) for g in ndef}}
    for g in G:
        res[g]={m:dict(c.most_common()) if m not in ('answers_per_file','choices_per_file','questions_per_file') else dict(sorted(c.items())) for m,c in G[g].items()}
    os.makedirs(a.out,exist_ok=True)
    json.dump(res,open(os.path.join(a.out,'corpus_stats.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    with open(os.path.join(a.out,'per_file.csv'),'w',newline='',encoding='utf-8') as fh:
        w=csv.writer(fh); w.writerow(['file','origin','encoding','bytes','directives','answers','choices','features']); w.writerows(rows)
    # markdown
    def tbl(m,g,k=25,tot=None):
        c=G[g].get(m,Counter()); t=tot or nfiles[g]
        s='| item | count |\n|---|---|\n'
        for x,v in c.most_common(k): s+=f'| `{x}` | {v} |\n'
        return s
    md=['# Corpus statistics (generated by oef_corpus_stats.py)\n',
        f"Files analysed: {dict(nfiles)} (e1..e5 test files excluded). `generated` = 1100 OEF emitted by the user's xml2oef converter; `all_upstream` = files from the WIMS 4.31b tarball.\n",
        '## Cumulative coverage tiers (files fully covered)\n','```json',json.dumps(tiers,indent=1),'```\n']
    for g in ('all_upstream','upstream_handwritten','upstream_models','generated'):
        md.append(f'\n# Group: {g} ({nfiles[g]} files)\n')
        for m,t in [('dir_files','Directives: number of files using it'),('dir_occ','Directives: total occurrences'),
                    ('answer_type','\\answer type= values (occurrences)'),('answer_type_files','\\answer type= (files)'),('choice_type_files','\\choice type= (files)'),('fn_files','special functions (files)'),('choice_type','\\choice type= values'),
                    ('answer_option_tokens','\\answer option= tokens'),('def_kind','Variable definitions by directive'),
                    ('fn_occ','Special functions called in definitions'),('slib_modules','slib() modules'),
                    ('wims_cmds','wims() sub-commands'),('cas_calls','CAS calls'),('language','\\language'),
                    ('title_lang','\\title_xx'),('computeanswer_values','\\computeanswer'),('precision_values','\\precision'),
                    ('embed_arg','\\embed argument shapes'),('special_arg','\\special first word'),
                    ('text_feature_files','Text features (files)'),('encoding','Encoding'),('questions_per_file','Questions (answer+choice) per file'),
                    ('flag','Flags')]:
            md.append(f'\n### {t}\n'); md.append(tbl(m,g,40))
        md.append(f"\nEmbed occurrences: {G[g].get('embed_occ')}, files with \\embed: {G[g].get('embed_files')}; \\special occurrences: {G[g].get('special_occ')}, files: {G[g].get('special_files')}\n")
        md.append(f"\nDirectives/file: {res['directives_per_file'][g]}; bytes/file: {res['bytes_per_file'][g]}; >1024 directives: {res['over_MAX_DEFINE_1024'][g]}; parse errors: {parse_err[g]}\n")
    open(os.path.join(a.out,'corpus_stats.md'),'w',encoding='utf-8').write('\n'.join(md))
    print(json.dumps({k:res[k] for k in ('files','parse_errors','tier_M1_mvp_scope','directives_per_file','over_MAX_DEFINE_1024')},indent=1))
if __name__=='__main__': main()
