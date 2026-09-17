#!/usr/bin/env python3
"""ChatGPT Artifact Preservation Audit v1.0.2.
Checks whether downloadable artifacts referenced in conversations physically exist in an export ZIP.
Keep chatgpt_archive_browser.py beside this file. Standard library only; read-only.
"""
from __future__ import annotations
import argparse,csv,html,io,json,re,sys,urllib.parse,zipfile
from collections import Counter,defaultdict
from pathlib import Path,PurePosixPath
from chatgpt_archive_browser import iter_array,active,msgtext

VERSION='1.0.2'
CONV=re.compile(r'(?:^|/)conversations(?:-\d+)?\.json$',re.I)
LIB=re.compile(r'(?:^|/)library[-_]files\.json$',re.I)
SID=re.compile(r'\b(?:file|asset)[-_][A-Za-z0-9]{6,}\b',re.I)
DOWN=re.compile(r'sandbox:/mnt/data/([^\s\)\]\}\>\"\']+)',re.I)
FSVC=re.compile(r'file-service://((?:file|asset)[-_][A-Za-z0-9]{6,})',re.I)
FENCE=re.compile(r'```(?:[\w+.#-]+)?\s*\n.*?```',re.S)
EXT={'.zip','.7z','.tar','.gz','.py','.ino','.c','.h','.cpp','.hpp','.js','.ts','.json','.yaml','.yml','.md','.txt','.pdf','.docx','.pptx','.csv','.xlsx','.uf2','.hex','.bin','.kicad_pcb','.kicad_sch','.kicad_pro','.sch','.brd','.pcb','.gbr','.drl','.step','.stp','.stl','.obj','.png','.jpg','.jpeg','.svg'}
STRUCT={'chat.html','library-files.json','library_files.json','user.json','account.json','feedback.json'}

def base(s):return PurePosixPath(urllib.parse.unquote(str(s or '')).replace('\\','/')).name
def key(s):return base(s).casefold()
def isart(s):
    n=key(s);return any(n.endswith(x) for x in EXT)
def flatten(v):
    if isinstance(v,dict):
        for x in v.values():yield from flatten(x)
    elif isinstance(v,list):
        for x in v:yield from flatten(x)
    elif isinstance(v,(str,int,float,bool)):yield str(v)

def physical(z):
    byn,byid=defaultdict(list),defaultdict(list);arts=[];infos=[i for i in z.infolist() if not i.is_dir()]
    for i in infos:
        byn[key(i.filename)].append(i)
        for fid in SID.findall(i.filename):byid[fid.casefold()].append(i)
        b=base(i.filename)
        if isart(b) and not CONV.search(i.filename) and b.casefold() not in STRUCT:arts.append(i)
    return infos,byn,byid,arts

def library(z,names):
    byn,byid=defaultdict(list),defaultdict(list);count=0;members=[n for n in names if LIB.search(n)]
    for n in members:
        try:r=json.load(io.TextIOWrapper(z.open(n),encoding='utf-8',errors='replace'))
        except Exception:continue
        recs=r if isinstance(r,list) else r.get('files',[]) if isinstance(r,dict) else []
        for j,rec in enumerate(recs):
            count+=1
            for s in flatten(rec):
                if isart(s):byn[key(s)].append((n,j))
                for fid in SID.findall(s):byid[fid.casefold()].append((n,j))
    return byn,byid,count,members

def scan(z,names):
    rows=[];seen=set();nconv=0;nmsg=0
    def add(c,m,kind,name='',fid='',inline=False):
        name=base(name) if name else '';k=(str(c.get('id') or c.get('conversation_id') or ''),str(m.get('id') or ''),kind,key(name),fid.casefold())
        if k in seen or (not name and not fid):return
        seen.add(k);rows.append({'conversation_id':k[0],'conversation_title':str(c.get('title') or 'Untitled'),'message_id':k[1],'message_role':str((m.get('author') or {}).get('role') or ''),'reference_kind':kind,'artifact_name':name,'file_id':fid,'inline_code':inline})
    for no,n in enumerate(names,1):
        print(f'[{no}/{len(names)}] {n}')
        with io.TextIOWrapper(z.open(n),encoding='utf-8',errors='replace') as f:
            for c in iter_array(f):
                nconv+=1
                for m in active(c):
                    nmsg+=1;t=msgtext(m);inline=bool(FENCE.search(t));ats=(m.get('metadata') or {}).get('attachments') or []
                    if isinstance(ats,list):
                        for a in ats:
                            if isinstance(a,dict):add(c,m,'attachment_metadata',a.get('name') or a.get('filename') or '',str(a.get('id') or a.get('file_id') or ''),inline)
                    for x in DOWN.finditer(t):add(c,m,'sandbox_download',x.group(1).rstrip('.,;:'),inline=inline)
                    for x in FSVC.finditer(t):add(c,m,'file_service_pointer',fid=x.group(1),inline=inline)
    return rows,nconv,nmsg

def resolve(rows,pn,pi,ln,li):
    used=set()
    for r in rows:
        hits=[]
        if r['artifact_name']:hits+=pn.get(key(r['artifact_name']),[])
        if r['file_id']:hits+=pi.get(r['file_id'].casefold(),[])
        hits=list({x.filename:x for x in hits}.values());lh=[]
        if r['artifact_name']:lh+=ln.get(key(r['artifact_name']),[])
        if r['file_id']:lh+=li.get(r['file_id'].casefold(),[])
        r['library_evidence']=bool(lh);r['physical_matches']=len(hits)
        if len(hits)==1:r['status']='PHYSICALLY_PRESERVED';r['physical_path']=hits[0].filename;used.add(hits[0].filename)
        elif len(hits)>1:r['status']='PHYSICAL_MATCH_AMBIGUOUS';r['physical_path']=' | '.join(x.filename for x in hits[:20])
        elif lh:r['status']='LIBRARY_REFERENCE_ONLY';r['physical_path']=''
        elif r['inline_code'] and (r['artifact_name'].casefold().endswith(('.zip','.py','.ino','.c','.h','.cpp','.hpp'))):r['status']='NOT_PHYSICAL_INLINE_CODE_EVIDENCE';r['physical_path']=''
        else:r['status']='REFERENCE_ONLY_NOT_PHYSICAL';r['physical_path']=''
    return used

def writecsv(p,rows,fields):
    with p.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def esc(x):return html.escape(str(x or ''))
def page(rows,counts,unref,nconv):
    trs=''.join(f"<tr><td>{esc(r['status'])}</td><td>{esc(r['artifact_name'] or r['file_id'])}</td><td>{esc(r['reference_kind'])}</td><td>{esc(r['conversation_title'])}</td><td>{esc(r['physical_path'])}</td><td>{'yes' if r['library_evidence'] else ''}</td><td>{'yes' if r['inline_code'] else ''}</td></tr>" for r in rows)
    return f'''<!doctype html><meta charset=utf-8><title>Artifact Preservation Audit</title><style>body{{font:15px system-ui;max-width:1400px;margin:30px auto;padding:0 20px;background:#f4f6fa}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}code{{background:#eee;padding:2px 4px}}.note{{background:#fff3c4;padding:12px}}</style><h1>ChatGPT Artifact Preservation Audit</h1><p class=note>Reference-only means no strong physical match was found in this export; it does not prove permanent loss. Inline code can aid reconstruction but is not the exact original package.</p><p><b>{nconv:,}</b> conversations · <b>{len(rows):,}</b> artifact references · <b>{counts.get('PHYSICALLY_PRESERVED',0):,}</b> physically preserved · <b>{counts.get('REFERENCE_ONLY_NOT_PHYSICAL',0):,}</b> reference-only · <b>{len(unref):,}</b> unreferenced physical artifact-like files</p><table><tr><th>Status</th><th>Artifact</th><th>Evidence</th><th>Conversation</th><th>Physical path</th><th>Library</th><th>Inline code</th></tr>{trs}</table>'''

def audit(zp,out):
    if not zipfile.is_zipfile(zp):raise ValueError('input must be a ChatGPT export ZIP')
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zp,'r',allowZip64=True) as z:
        names=z.namelist();cn=sorted(n for n in names if CONV.search(n))
        if not cn:raise ValueError('no conversations JSON files found')
        infos,pn,pi,arts=physical(z);ln,li,lcount,lmembers=library(z,names);rows,nconv,nmsg=scan(z,cn);used=resolve(rows,pn,pi,ln,li)
        unref=[{'path':i.filename,'size':i.file_size} for i in arts if i.filename not in used]
    counts=Counter(r['status'] for r in rows);fields=['status','artifact_name','file_id','reference_kind','message_role','conversation_title','conversation_id','message_id','physical_matches','physical_path','library_evidence','inline_code']
    writecsv(out/'artifact_audit.csv',rows,fields);writecsv(out/'unreferenced_physical_artifacts.csv',unref,['path','size'])
    summary={'tool':'ChatGPT Artifact Preservation Audit','version':VERSION,'conversations':nconv,'messages':nmsg,'artifact_references':len(rows),'library_records':lcount,'library_manifest_members':lmembers,'physical_files':len(infos),'physical_artifact_like_files':len(arts),'status_counts':dict(counts),'unreferenced_physical_artifacts':len(unref)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');(out/'index.html').write_text(page(rows,counts,unref,nconv),encoding='utf-8')
    print('\nSummary');print('  Conversations:',nconv);print('  Artifact references:',len(rows));[print(' ',k+':',v) for k,v in counts.items()];print('  Report:',out/'index.html')

def main():
    p=argparse.ArgumentParser();p.add_argument('zipfile',type=Path);p.add_argument('-o','--output',type=Path,default=Path('ChatGPT_Artifact_Audit'));p.add_argument('--version',action='version',version=VERSION);a=p.parse_args()
    try:
        if a.output.exists() and any(a.output.iterdir()):raise ValueError(f'output folder is not empty: {a.output}')
        audit(a.zipfile,a.output);return 0
    except Exception as e:print('ERROR:',e,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
