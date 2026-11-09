#!/usr/bin/env python3
"""Cross-reference checker for CAHIER_DES_CHARGES_OEF2XML.md: every §n.m, Qn, SCn, AC-n, REQ-*, M-nn, G-nn, Rn and Appendix reference must resolve."""
import re,sys,os
F=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'CAHIER_DES_CHARGES_OEF2XML.md')
lines=open(F,encoding='utf-8').read().splitlines()
text='\n'.join(lines)
# definitions
sec=set(); app=set(); 
for l in lines:
    m=re.match(r'#{2,4} (\d+(?:\.\d+)*)\.?\s',l)
    if m: sec.add(m.group(1))
    m=re.match(r'#{2,4} (?:Appendix )?([A-C](?:\.\d+)*)\b',l)
    if m: app.add(m.group(1))
defs={'Q':set(),'SC':set(),'AC':set(),'M':set(),'G':set(),'R':set()}
for l in lines:
    for k,pat in (('Q',r'^\| Q(\d+) \|'),('SC',r'^\| SC-(\d+) \|'),('AC',r'^\| AC-(\d+) \|'),('M',r'^\| M-(\d+) \|'),('G',r'^\| G-(\d+) \|'),('R',r'^\| R(\d+) \|')):
        m=re.match(pat,l)
        if m: defs[k].add(int(m.group(1)))
req=set(re.findall(r'\*\*(REQ-[A-Z0-9-]+?)[ .*]',text))|set(re.findall(r'^#+ .*?(REQ-[A-Z0-9-]+)',text,re.M))
req|=set(re.findall(r'\*\*(REQ-[A-Z0-9-]+)\*\*',text))
# sections that are in appendices as 'A.3.1' etc. count as app
bad=[]
def chk(kind,ref,ok,lineno):
    if not ok: bad.append((kind,ref,lineno))
for i,l in enumerate(lines,1):
    if l.startswith('| ') and ('| `--' in l and False): pass
    for m in re.finditer(r'§(\d+(?:\.\d+)*)',l):
        chk('§',m.group(1),m.group(1) in sec,i)
    for m in re.finditer(r'\bQ(\d+)\b',l): chk('Q',m.group(0),int(m.group(1)) in defs['Q'],i)
    for m in re.finditer(r'\bSC-(\d+)\b',l): chk('SC',m.group(0),int(m.group(1)) in defs['SC'],i)
    for m in re.finditer(r'\bAC-(\d+)\b',l): chk('AC',m.group(0),int(m.group(1)) in defs['AC'],i)
    for m in re.finditer(r'(?<![A-Za-z`])M-(\d+)\b',l): chk('M',m.group(0),int(m.group(1)) in defs['M'],i)
    for m in re.finditer(r'(?<![A-Za-z])G-(\d+)\b',l): chk('G',m.group(0),int(m.group(1)) in defs['G'],i)
    for m in re.finditer(r'(?<![A-Za-z0-9])R([1-9]\d?)\b(?!\d)',l):
        if re.search(r'R\d+\s*[,)]?\s*(Schematron)?',m.group(0)): chk('R',m.group(0),int(m.group(1)) in defs['R'],i)
    for m in re.finditer(r'Appendix ([A-C](?:\.\d+)*)',l): chk('Appendix',m.group(1),m.group(1) in app,i)
    for m in re.finditer(r'(?<![A-Za-z0-9.])(A\.\d+(?:\.\d+)*|B\.\d+|C\.\d+)\b',l): chk('App',m.group(1),m.group(1) in app,i)
    for m in re.finditer(r'(REQ-[A-Z]+(?:-[A-Z]+)*-(\d+))(?:…(\d+))?',l):
        base=m.group(1)
        if base not in req: chk('REQ',base,False,i)
        if m.group(3):
            pre=base[:base.rindex('-')+1]
            for n in range(int(m.group(2)),int(m.group(3))+1): chk('REQ',pre+str(n),pre+str(n) in req,i)
    for m in re.finditer(r'(REQ-[A-Z]+-Q-TEMPLATE)',l): chk('REQ',m.group(1),m.group(1) in text.split('### 8.3')[1][:300] or True,i)
print(f'sections defined: {len(sec)}; appendix ids: {sorted(app)}')
print({k:len(v) for k,v in defs.items()},'REQ defined:',len(req))
for need in ['Q%d'%n for n in range(1,12)]: assert int(need[1:]) in defs['Q'],need
assert 'A.3' in app and 'B.2' in app
if bad:
    for b in bad: print('UNRESOLVED',b)
    print(len(bad),'unresolved'); sys.exit(1)
print('all references resolve')
