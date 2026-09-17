#!/usr/bin/env python3
"""ChatGPT Library Audit v1.0.0 - local, read-only, standard-library only."""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,html,io,json,re,shutil,zipfile
from collections import Counter,defaultdict
from pathlib import Path,PurePosixPath

VERSION='1.0.0'
MANIFEST={'library-files.json','library_files.json'}
STRUCT=[re.compile(x,re.I) for x in [r'(^|/)conversations(?:-\d+)?\.json$',r'(^|/)chat\.html$',r'(^|/)library[-_]files\.json$']]
IDRX=re.compile(r'(?:file|asset)[-_][A-Za-z0-9]{6,}',re.I)
HASHRX=re.compile(r'\b[a-fA-F0-9]{64}\b')

def flat(x,p=''):
    if isinstance(x,dict):
        for k,v in x.items():
            q=f'{p}.{k}' if p else str(k)
            if isinstance(v,(dict,list)): yield from flat(v,q)
            else: yield q,v
    elif isinstance(x,list):
        for i,v in enumerate(x):
            q=f'{p}[{i}]'
            if isinstance(v,(dict,list)): yield from flat(v,q)
            else: yield q,v

def base(s): return PurePosixPath(str(s).replace('\\','/')).name.lower()
def norm(s): return re.sub(r'/+','/',re.sub(r'^[a-zA-Z]+://','',str(s).replace('\\','/').strip()).lstrip('/')).lower()
def structural(n): return any(r.search(n) for r in STRUCT)
def hb(n):
    if n is None:return ''
    x=float(n)
    for u in ['B','KB','MB','GB','TB']:
        if x<1024 or u=='TB': return f'{x:.0f} {u}' if u=='B' else f'{x:.2f} {u}'
        x/=1024

def records(obj):
    if isinstance(obj,list): return [x for x in obj if isinstance(x,dict)]
    if isinstance(obj,dict):
        for k in ['files','items','records','library_files','library-files','data']:
            if isinstance(obj.get(k),list): return [x for x in obj[k] if isinstance(x,dict)]
        if obj and all(isinstance(v,dict) for v in obj.values()): return list(obj.values())
    return []

def meta(r):
    fs=list(flat(r)); paths=[];ids=set();sizes=set();hashes=set();bases=[]
    for k,v in fs:
        kl=k.lower()
        if isinstance(v,str) and v:
            if re.search(r'path|file|filename|file_name|name|download|uri|url|asset|pointer|location',kl):
                if '/' in v or '\\' in v or '.' in base(v) or IDRX.search(v): paths.append(v);bases.append(base(v))
            ids.update(t.lower() for t in IDRX.findall(v))
            if re.search(r'(^|_)(id|file_id|asset_id|upload_id)($|_)',kl): ids.add(v.lower())
            if re.search(r'sha256|checksum|hash',kl): hashes.update(h.lower() for h in HASHRX.findall(v))
        if isinstance(v,(int,float)) and not isinstance(v,bool) and v>=0 and re.search(r'(^|_)(size|bytes|file_size|content_length)($|_)',kl): sizes.add(int(v))
    def pick(keys):
        for k in keys:
            if r.get(k) not in (None,''): return str(r[k])[:300]
        return ''
    name=pick(['name','filename','file_name','title','display_name','original_name']) or (bases[0] if bases else '')
    rid=pick(['id','file_id','asset_id','upload_id']) or (sorted(ids)[0] if ids else '')
    return dict(paths=paths,bases=list(dict.fromkeys(x for x in bases if x)),ids=sorted(ids),sizes=sorted(sizes),hashes=sorted(hashes),display_name=name,record_id=rid,mime=pick(['mime_type','content_type','mimetype','media_type']),origin=pick(['source','origin','kind','type','use_case','generation_type']))

def indexes(es):
    p=defaultdict(list);b=defaultdict(list);i=defaultdict(list);s=defaultdict(list);stem=defaultdict(list)
    for n,e in enumerate(es):
        p[norm(e['name'])].append(n);bn=base(e['name']);b[bn].append(n);stem[PurePosixPath(bn).stem.lower()].append(n);s[e['size']].append(n)
        for t in IDRX.findall(e['name']):i[t.lower()].append(n)
    return p,b,i,stem,s

def sha(z,name):
    h=hashlib.sha256()
    with z.open(name) as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()

def match(m,es,ix,z,hashmode,cache):
    p,b,i,stem,s=ix;score=defaultdict(int);why=defaultdict(list)
    for x in m['paths']:
        for n in p.get(norm(x),[]):score[n]+=100;why[n].append('exact path')
        for n in b.get(base(x),[]):score[n]+=45;why[n].append('basename')
    for x in m['bases']:
        for n in b.get(x,[]):score[n]+=45;why[n].append('basename')
    for x in m['ids']:
        for n in i.get(x,[]):score[n]+=80;why[n].append('file/asset id')
        for n in stem.get(x,[]):score[n]+=70;why[n].append('id equals filename stem')
    for x in m['sizes']:
        for n in s.get(x,[]):score[n]+=12;why[n].append('size')
    if hashmode and m['hashes']:
        cand=set(score)
        if not cand:
            for x in m['sizes']:cand.update(s.get(x,[]))
        for n in cand:
            if n not in cache:cache[n]=sha(z,es[n]['name'])
            if cache[n].lower() in m['hashes']:score[n]+=200;why[n].append('sha256')
    if not score:return 'missing',None,0,'no matching export entry',[]
    ranked=sorted(score.items(),key=lambda q:(-q[1],es[q[0]]['name'].lower()));best,sc=ranked[0];ties=[n for n,x in ranked if x==sc]
    if sc<40:return 'missing',None,sc,'only weak evidence (for example size)',[es[n]['name'] for n in ties[:5]]
    if len(ties)>1:return 'ambiguous',None,sc,'; '.join(sorted(set(why[best]))),[es[n]['name'] for n in ties[:10]]
    return 'matched',best,sc,'; '.join(sorted(set(why[best]))),[]

def csvout(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def report(summary,rows,unmatched):
    data=json.dumps(rows,ensure_ascii=False,separators=(',',':')).replace('</','<\\/');und=json.dumps(unmatched,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChatGPT Library Audit</title><style>body{{margin:0;background:#f4f7fb;color:#172333;font:15px/1.5 system-ui}}header{{background:#234a80;color:#fff;padding:30px}}main{{max-width:1250px;margin:auto;padding:20px}}.warn{{background:#fff3c4;padding:12px;border-radius:9px}}.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}}.s{{background:#fff;border:1px solid #dce4ee;border-radius:10px;padding:12px}}.s b{{display:block;font-size:24px}}input,select{{padding:9px;margin:8px 4px 8px 0}}table{{width:100%;border-collapse:collapse;background:#fff}}th,td{{padding:8px;border-bottom:1px solid #dce4ee;text-align:left;vertical-align:top}}th{{background:#edf2f8}}tr.matched td:first-child{{background:#e8f7ee}}tr.ambiguous td:first-child{{background:#fff4cf}}tr.missing td:first-child{{background:#fdeaea}}code{{font-size:12px;overflow-wrap:anywhere}}details{{background:#fff;padding:12px;margin:16px 0;border:1px solid #dce4ee;border-radius:9px}}@media(max-width:900px){{.stats{{grid-template-columns:1fr 1fr}}}}</style></head><body><header><h1>ChatGPT Library Audit</h1><p>Manifest records compared with physical files actually present in the supplied export.</p></header><main><p class="warn"><b>Keep this report private.</b> Filenames and metadata may be sensitive.</p><div class="stats"><div class=s><b>{summary['library_records']}</b>Library records</div><div class=s><b>{summary['matched']}</b>Matched</div><div class=s><b>{summary['ambiguous']}</b>Ambiguous</div><div class=s><b>{summary['missing']}</b>Missing</div><div class=s><b>{summary['unmatched_physical']}</b>Unmatched physical</div></div><p><b>Manifest:</b> {html.escape(', '.join(summary['manifest_files']) or 'NOT FOUND')}<br><small>Size alone never counts as a match. Missing means "not strongly matched," not "proved deleted."</small></p><input id=q placeholder="Search records"><select id=st><option value="">All statuses</option><option>matched</option><option>ambiguous</option><option>missing</option></select><p id=count></p><div style="overflow:auto;max-height:70vh"><table><thead><tr><th>Status</th><th>Library item</th><th>ID</th><th>Type/origin</th><th>Matched export file</th><th>Evidence</th></tr></thead><tbody id=rows></tbody></table></div><details><summary><b>Unmatched physical files ({len(unmatched)})</b></summary><p>Not automatically errors; they may belong to conversations or other export features.</p><div id=un></div></details></main><script id=d type="application/json">{data}</script><script id=u type="application/json">{und}</script><script>const A=JSON.parse(d.textContent),U=JSON.parse(u.textContent),E=s=>String(s??'').replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));function draw(){{let Q=q.value.toLowerCase(),S=st.value,F=A.filter(x=>(!S||x.status==S)&&(!Q||JSON.stringify(x).toLowerCase().includes(Q)));count.textContent=F.length+' records shown';rows.innerHTML=F.map(x=>`<tr class="${{E(x.status)}}"><td><b>${{E(x.status)}}</b></td><td>${{E(x.display_name||'(unnamed)')}}</td><td><code>${{E(x.record_id)}}</code></td><td>${{E([x.mime,x.origin].filter(Boolean).join(' · '))}}</td><td><code>${{E(x.matched_file||x.candidates||'')}}</code></td><td>${{E(x.reason)}}${{x.score?' ('+x.score+')':''}}</td></tr>`).join('')}}q.oninput=st.onchange=draw;un.innerHTML=U.map(x=>`<div><code>${{E(x.name)}}</code> — ${{E(x.size_human)}}</div>`).join('');draw();</script></body></html>'''

def audit(inp,out,hashmode=False,overwrite=False):
    if out.exists():
        if not overwrite:raise FileExistsError(f'{out} exists; use --overwrite')
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if not inp.is_file() or not zipfile.is_zipfile(inp):raise ValueError('Input must be the original ChatGPT export ZIP.')
    with zipfile.ZipFile(inp,'r',allowZip64=True) as z:
        entries=[{'name':x.filename,'size':x.file_size} for x in z.infolist() if not x.is_dir()]; mans=[e['name'] for e in entries if base(e['name']) in MANIFEST];phys=[e for e in entries if not structural(e['name'])];ix=indexes(phys);allrec=[]
        for mn in mans:
            with z.open(mn) as b:
                obj=json.load(io.TextIOWrapper(b,encoding='utf-8-sig',errors='replace'))
            allrec.extend((mn,r) for r in records(obj))
        rows=[];used=set();cache={}
        for num,(mn,r) in enumerate(allrec,1):
            m=meta(r);st,n,sc,why,cand=match(m,phys,ix,z,hashmode,cache);mf='';ms=None
            if st=='matched':used.add(n);mf=phys[n]['name'];ms=phys[n]['size']
            rows.append(dict(record_number=num,manifest=mn,status=st,display_name=m['display_name'],record_id=m['record_id'],mime=m['mime'],origin=m['origin'],matched_file=mf,matched_size=ms,reason=why,score=sc,candidates=' | '.join(cand)))
        un=[dict(name=e['name'],size=e['size'],size_human=hb(e['size'])) for n,e in enumerate(phys) if n not in used];c=Counter(r['status'] for r in rows)
        summary=dict(tool_version=VERSION,generated_at=dt.datetime.now().astimezone().isoformat(timespec='seconds'),source=inp.name,manifest_files=mans,library_records=len(rows),matched=c['matched'],ambiguous=c['ambiguous'],missing=c['missing'],unmatched_physical=len(un),physical_nonstructural_entries=len(phys),physical_nonstructural_bytes=sum(e['size'] for e in phys),hash_mode=hashmode)
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');(out/'library_audit.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8');csvout(out/'library_audit.csv',rows,['record_number','status','display_name','record_id','mime','origin','manifest','matched_file','matched_size','reason','score','candidates']);csvout(out/'unmatched_physical_files.csv',un,['name','size','size_human']);(out/'index.html').write_text(report(summary,rows,un),encoding='utf-8');(out/'README.txt').write_text('Open index.html. Keep this report private. The original export was not modified.\n',encoding='utf-8');return summary

def main():
    p=argparse.ArgumentParser(description='Audit library-files.json against physical files in a ChatGPT export ZIP.');p.add_argument('input',type=Path);p.add_argument('-o','--output',type=Path,default=Path('ChatGPT_Library_Audit'));p.add_argument('--hash',action='store_true');p.add_argument('--overwrite',action='store_true');p.add_argument('--version',action='version',version=VERSION);a=p.parse_args()
    try:s=audit(a.input,a.output,a.hash,a.overwrite)
    except Exception as e:print('ERROR:',e);return 1
    print('Library manifest files:',len(s['manifest_files']))
    if not s['manifest_files']:print('No library-files.json found. Check that you used the ORIGINAL FULL export ZIP.')
    print(f"Library records: {s['library_records']} | Matched: {s['matched']} | Ambiguous: {s['ambiguous']} | Missing: {s['missing']}")
    print('Report:',a.output/'index.html');return 0
if __name__=='__main__':raise SystemExit(main())
