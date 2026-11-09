#!/usr/bin/env python3
"""Catalogue of XML block types/fields/inputs observed in a folder of XML program files
(urn:eleda:program:v1), cross-checked against the block-type-enum of the Relax NG schema.
Usage: python3 xml_block_catalog.py [--xml DIR] [--rng schema.rng] [--out DIR]"""
import argparse, os, re, json, collections
import xml.etree.ElementTree as ET
NS='{urn:eleda:program:v1}'
ap=argparse.ArgumentParser()
ap.add_argument('--xml',default='/workspace/xml_etudes')
ap.add_argument('--rng',default='/home/box/sand-data/agents/9762ce64-b543-44f1-93c3-9f8b55f8ceb1/attachments/e744b791e7f1084bfe8bb9b6731b29e8f4c21285c7606a085ead93369baade29.xml')
ap.add_argument('--out',default='/workspace/oef2xml')
a=ap.parse_args()
rng=open(a.rng,encoding='utf-8').read()
enum_txt=rng[rng.index('<define name="block-type-enum">'):rng.index('<define name="any-content">')]
enum=set(re.findall(r'<value>([^<]+)</value>',enum_txt))
blocks=collections.Counter(); files_with=collections.defaultdict(set)
fields=collections.defaultdict(collections.Counter); inputs=collections.defaultdict(collections.Counter)
extra=collections.defaultdict(collections.Counter); fieldvals=collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
settings=collections.Counter(); langs=collections.Counter(); srcfmt=collections.Counter(); nq=collections.Counter()
rootkids=collections.Counter(); top_blocks=collections.Counter(); shadows=collections.Counter()
nfiles=0
for fn in sorted(os.listdir(a.xml)):
    if not fn.endswith('.xml'): continue
    try: root=ET.parse(os.path.join(a.xml,fn)).getroot()
    except ET.ParseError: continue
    nfiles+=1
    srcfmt[root.get('source_format')]+=1
    for c in root: rootkids[c.tag.replace(NS,'')]+=1
    for s in root.iter(NS+'settings'):
        for c in s: settings[c.tag.replace(NS,'')]+=1
    for l in root.iter(NS+'lang'): langs[l.get('code')]+=1
    b=root.find(NS+'blocks')
    for c in b: top_blocks[c.get('type')]+=1
    q=0
    for e in root.iter():
        t=e.tag.replace(NS,'')
        if t=='block':
            ty=e.get('type'); blocks[ty]+=1; files_with[ty].add(fn)
            if ty.startswith('question_') or ty=='QUESTION': q+=1
            for c in e:
                ct=c.tag.replace(NS,'')
                if ct=='field':
                    fields[ty][c.get('name')]+=1
                    v=(c.text or '').strip()
                    if len(v)<40 and not re.fullmatch(r'[A-Za-z0-9_!~\[\]\{\}\(\)\$#%^*+/:.,;?@|=`-]{20}',c.get('name') or ''): fieldvals[ty][c.get('name')][v]+=1
                elif ct=='input': inputs[ty][c.get('name')]+=1
                elif ct=='extraState':
                    for cc in c: extra[ty][cc.tag.replace(NS,'')]+=1
        elif t=='shadow': shadows[e.get('type')]+=1
    nq[q]+=1
out={'xml_files':nfiles,'source_format':dict(srcfmt),'root_children':dict(rootkids),'settings_keys':dict(settings),'langs':dict(langs),
 'top_level_blocks':dict(top_blocks.most_common()),'questions_per_program':dict(sorted(nq.items())),
 'distinct_block_types':len(blocks),'types_in_enum':sum(1 for t in blocks if t in enum),
 'types_NOT_in_enum_(accepted_only_by_catch-all_pattern)':{t:blocks[t] for t in blocks if t not in enum},
 'enum_size':len(enum),'enum_types_never_observed':sorted(enum-set(blocks)),
 'shadow_types':dict(shadows.most_common()),
 'blocks':{t:{'count':n,'programs':len(files_with[t]),'in_enum':t in enum,'fields':dict(fields[t].most_common()),
              'inputs':dict(inputs[t].most_common()),'extraState':dict(extra[t].most_common()),
              'field_values':{k:dict(v.most_common(12)) for k,v in fieldvals[t].items()} if t in fieldvals else {}}
          for t,n in blocks.most_common()}}
json.dump(out,open(os.path.join(a.out,'xml_block_catalog.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(nfiles,'files;',len(blocks),'types;',out['types_in_enum'],'in enum; not in enum:',out['types_NOT_in_enum_(accepted_only_by_catch-all_pattern)'])
