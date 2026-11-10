#!/usr/bin/env python3
"""Upper bounds on the share of OEF files the planned converter can classify complet / partiel (spec section 14.2).
Re-uses the parser of oef_corpus_stats.py. A file is 'complet-eligible' if EVERY construct it uses is inside the planned
final scope; 'partiel-eligible' if it has >=1 answer/choice of a non-gap type. Both are UPPER bounds (they ignore taint,
unparseable expressions and anything not visible at directive level).
Usage: python3 scope_bounds.py [--corpus DIR] [--map corpus.map] [--out FILE.json]"""
import argparse, json, os, re, importlib.util
from collections import Counter
here=os.path.dirname(os.path.abspath(__file__))
spec=importlib.util.spec_from_file_location('s',os.path.join(here,'oef_corpus_stats.py')); s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
ap=argparse.ArgumentParser(); ap.add_argument('--corpus',default='/workspace/oefc/corpus'); ap.add_argument('--map',default='/workspace/oefc/corpus.map'); ap.add_argument('--out',default=os.path.join(here,'scope_bounds.json')); a=ap.parse_args()
origin={}
for l in open(a.map,encoding='utf-8'):
    f,_,p=l.rstrip('\n').partition('\t')
    origin[f]='generated' if '/oef_out/' in p else 'class' if '/log/classes/' in p else 'model' if '/scripts/model/' in p else 'module'
# planned final scope (spec section 6/7/8)
DIR_OK={'title','language','author','email','keywords','description','credits','css','observation','computeanswer','precision','range','format',
 'integer','int','real','rational','text','complex','function','matrix','parameter','variable','statement','answer','reply','choice',
 'if','ifval','for','while','else','endif','next','endwhile','feedback','title_en','title_fr','title_es','title_it','title_ca','title_cn','title_nl','title_si'}
DIR_COND={'condition','conditions'}                     # only for the forward-emitted pattern (generated corpus)
FN_OK={'randint','random','shuffle','randitem','randomitem','pickone','item','items','row','rows','column','position','positionof','randrow','randomrow','evalue','evaluate','diff','deriv','derivative','simplify','asis','texmath','htmlmath','wims'}
FN_CAS={'pari','maxima'}                                # only forward-emitted patterns (generated corpus)
SUBCMD_OK={'replace','lowercase','uppercase','charcnt','char','sort'}   # reverse subset of section 7.3
ANS_OK={'numeric','number','radio','checkbox','correspond','corresp','reorder','default','case','nocase','atext','text','raw','chset','formal','algexp','expalg','numexp','function','equation','litexp','symtext','menu','select','range','ranges'}
# v0.2.6 always-gap HTML list (spec M-48 / G-19): script form input style link meta base object embed iframe, on*= attributes, javascript:/vbscript:/data:text/html URLs
HTML_ACTIVE=r'<\s*(?:script|form|input|style|link|meta|base|object|embed|iframe)\b|<[^<>]*\s+on[a-z]+\s*=|(?:javascript|vbscript)\s*:|data\s*:\s*text/html'
res={}
for f,o in origin.items():
    t,_=s.decode(open(os.path.join(a.corpus,f),'rb').read()); d,err=s.parse(t)
    g='generated' if o=='generated' else 'upstream_handwritten' if o in('class','module') else 'upstream_models'
    gen=(g=='generated')
    names={n for n,_ in d}; q=0; ok_q=0; bad=set(); dyn=False
    for n,ps in d:
        if n in('answer','reply','choice'):
            q+=1
            if n=='choice': ok_q+=1; continue
            pos,opts=s.split_answer_params(ps); ty=opts.get('type','(none)').strip().lower().split()[0] if opts.get('type','').strip() or 'type' not in opts else '(none)'
            if 'type' not in opts: ty='(none)'
            if ty.startswith('\\'): dyn=True; bad.add('dyn-type')
            elif ty=='(none)' or ty in ANS_OK: ok_q+=1
            else: bad.add('ans:'+ty)
        elif n in s.DEFS or n in('condition','conditions'):
            code=' '.join(ps)
            for fn in s.SPECIAL_FN:
                if re.search(r'(?<![\w\\])'+fn+r'\s*\(',code):
                    if fn in FN_OK or (gen and fn in FN_CAS): pass
                    else: bad.add('fn:'+fn)
            for m in re.finditer(r'(?<![\w\\])wims\s*\(\s*([A-Za-z0-9_]+)',code):
                if not gen and m.group(1) not in SUBCMD_OK: bad.add('wims:'+m.group(1))
    for n in names:
        if n in DIR_OK: continue
        if n in DIR_COND and gen: continue
        bad.add('dir:'+n)
    if re.search(r'\\special\s*\{',t): bad.add('special')
    if re.search(HTML_ACTIVE,t,re.I): bad.add('html-active')       # G-19 family (v0.2.6): always a gap, any --html mode
    if gen and 'x2o NON TRADUIT' in t: bad.add('x2o-NON-TRADUIT')   # REQ-IDIOM-1: XML block lost by the forward converter
    c=res.setdefault(g,Counter()); c['files']+=1
    if ok_q>0 and not dyn: c['partiel_eligible']+=1
    if ok_q>0 and q==ok_q and not bad: c['complet_eligible']+=1
    if dyn or ok_q==0: c['no_convertible_question']+=1
    for b in bad: c['blocker:'+b.split(':')[0]]+=1
    res.setdefault(g+'_blockers',Counter()).update(set(bad))
out={g:dict(c.most_common()) if not g.endswith('_blockers') else dict(c.most_common(25)) for g,c in res.items()}
res_all=Counter()
json.dump(out,open(a.out,'w',encoding='utf-8'),indent=1,ensure_ascii=False)
for g in ('upstream_handwritten','upstream_models','generated'):
    c=res[g]; n=c['files']; print(g,n,'complet<=',c['complet_eligible'],round(100*c['complet_eligible']/n),'% | partiel_eligible',c['partiel_eligible'],round(100*c['partiel_eligible']/n),'% | no convertible question',c['no_convertible_question'])
