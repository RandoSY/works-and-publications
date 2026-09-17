#!/usr/bin/env python3
"""ChatGPT Artifact Preservation Audit v1.0.1.
Read-only audit: did downloadable artifacts referenced by conversations physically survive?
Requires chatgpt_archive_browser.py in the same folder. Standard library only.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,html,io,json,re,sys,urllib.parse,zipfile
from collections import Counter,defaultdict
from pathlib import Path,PurePosixPath
from chatgpt_archive_browser import iter_array, active, msgtext

VERSION='1.0.1'
CONV_RX=re.compile(r'(?:^|/)conversations(?:-\d+)?\.json$',re.I)
LIB_RX=re.compile(r'(?:^|/)library[-_]files\.json$',re.I)
ID_RX=re.compile(r'\b(?:file|asset)[-_][A-Za-z0-9]{6,}\b',re.I)
SANDBOX_RX=re.compile(r'sandbox:/mnt/data/([^\s\)\]\}\>\"\']+)',re.I)
FILESVC_RX=re.compile(r'file-service://((?:file|asset)[-_][A-Za-z0-9]{6,})',re.I)
CODE_RX=re.compile(r'```(?:[A-Za-z0-9_+.#-]+)?\s*\n.*?```',re.S)
ARCH={'.zip','.7z','.tar','.gz','.tgz','.bz2','.xz'}
CODE={'.py','.pyw','.ino','.c','.h','.cc','.cpp','.cxx','.hpp','.hh','.js','.mjs','.cjs','.ts','.tsx','.jsx','.java','.cs','.go','.rs','.sh','.bash','.ps1','.bat','.cmd','.html','.htm','.css','.json','.yaml','.yml','.toml','.xml','.sql','.asm','.s','.forth','.fs','.fth','.uf2','.hex','.bin','.elf','.map','.cmake','.mk'}
DOC={'.md','.txt','.pdf','.doc','.docx','.rtf','.odt','.ppt','.pptx'}
DATA={'.csv','.tsv','.xls','.xlsx','.ods','.sqlite','.db','.parquet'}
CAD={'.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_prl','.sch','.brd','.pcb','.gbr','.drl','.step','.stp','.stl','.obj','.fcstd'}
IMG={'.png','.jpg','.jpeg','.gif','.webp','.svg','.bmp','.tif','.tiff'}
EXTS=ARCH|CODE|DOC|DATA|CAD|IMG
STRUCT={'chat.html','library-files.json','library_files.json','user.json','account.json','shared_conversations.json','feedback.json'}

def suffix(name):
    low=str(name).casefold()
    for e in sorted(EXTS,key=len,reverse=True):
        if low.endswith(e): return e
    return PurePosixPath(low).suffix

def artclass(name):
    e=suffix(name)
    if e in ARCH:return 'archive/package'
    if e in CODE:return 'code/firmware'
    if e in CAD:return 'CAD/PCB/model'
    if e in DOC:return 'document'
    if e in DATA:return 'data/spreadsheet'
    if e in IMG:return 'image'
    return 'other'

def isart(name):return suffix(name) in EXTS

def norm(s):
    s=urllib.parse.unquote(str(s or '')).replace('\\','/')
    return PurePosixPath(s).name.casefold()

def iso(ts):
    try:return dt.datetime.fromtimestamp(float(ts),tz=dt.timezone.utc).isoformat()
    except:return ''

def scalars(v):
    if isinstance(v,dict):
        for x in v.values():yield from scalars(x)
    elif isinstance(v,list):
        for x in v:yield from scalars(x)
    elif isinstance(v,(str,int,float,bool)) and v is not None:yield str(v)

def lib_index(z,names):
    bn,bi=defaultdict(list),defaultdict(list); count=0; members=[n for n in names if LIB_RX.search(n)]
    for n in members:
        try:raw=json.load(io.TextIOWrapper(z.open(n),encoding='utf-8',errors='replace'))
        except:continue
        recs=raw if isinstance(raw,list) else raw.get('files') if isinstance(raw,dict) and isinstance(raw.get('files'),list) else [raw]
        for i,r in enumerate(recs):
            count+=1
            for s in scalars(r):
                if isart(s):bn[norm(s)].append((n,i))
                for fid in ID_RX.findall(s):bi[fid.casefold()].append((n,i))
    return bn,bi,count,members

def physical_index(z):
    bn,bi=defaultdict(list),defaultdict(list); arts=[]; infos=[i for i in z.infolist() if not i.is_dir()]
    for i in infos:
        b=PurePosixPath(i.filename).name;bn[norm(b)].append(i)
        for fid in ID_RX.findall(i.filename):bi[fid.casefold()].append(i)
        if isart(b) and not CONV_RX.search(i.filename) and b.casefold() not in STRUCT:arts.append(i)
    return infos,bn,bi,arts

def add(refs,conv,msg,kind,name='',fid='',size='',mime='',evidence='',inline=False):
    name=PurePosixPath(urllib.parse.unquote(name).replace('\\','/')).name if name else ''
    if not name and not fid:return
    key=(str(conv.get('conversation_id') or conv.get('id') or ''),str(msg.get('id') or ''),kind,norm(name),fid.casefold())
    if key in refs:return
    refs[key]={'conversation_id':key[0],'conversation_title':str(conv.get('title') or 'Untitled'),'conversation_date':iso(conv.get('create_time')),'message_id':key[1],'message_role':str((msg.get('author') or {}).get('role') or 'unknown'),'reference_kind':kind,'artifact_name':name,'artifact_class':artclass(name) if name else 'unknown','file_id':fid,'reported_size':size if isinstance(size,(int,float)) else '','mime_type':mime,'evidence':evidence[:400],'inline_code_in_message':bool(inline)}

def scan(z,convnames):
    refs={};stats=Counter()
    for j,n in enumerate(convnames,1):
        print(f'[{j}/{len(convnames)}] scanning {n}')
        with io.TextIOWrapper(z.open(n),encoding='utf-8',errors='replace') as fp:
            for c in iter_array(fp):
                stats['conversations']+=1
                for m in active(c):
                    stats['messages']+=1;text=msgtext(m);inline=bool(CODE_RX.search(text))
                    if inline:stats['messages_with_code']+=1
                    md=m.get('metadata') or {};ats=md.get('attachments') or []
                    if isinstance(ats,list):
                        for a in ats:
                            if not isinstance(a,dict):continue
                            name=str(a.get('name') or a.get('filename') or '');fid=str(a.get('id') or a.get('file_id') or '')
                            size=a.get('size') or a.get('size_bytes') or a.get('file_token_size') or a.get('fileTokenSize') or ''
                            mime=str(a.get('mime_type') or a.get('mimeType') or '')
                            add(refs,c,m,'attachment_metadata',name,fid,size,mime,f'attachment metadata: {name or fid}',inline)
                    for x in SANDBOX_RX.finditer(text):
                        name=x.group(1).rstrip('.,;:');add(refs,c,m,'sandbox_download',name,evidence=f'sandbox:/mnt/data/{name}',inline=inline)
                    for x in FILESVC_RX.finditer(text):add(refs,c,m,'file_service_pointer',fid=x.group(1),evidence=x.group(0),inline=inline)
    return list(refs.values()),stats

def resolve(refs,pn,pi,ln,li):
    used=set()
    for r in refs:
        cs=[]
        if r['artifact_name']:cs+=pn.get(norm(r['artifact_name']),[])
        if r['file_id']:cs+=pi.get(r['file_id'].casefold(),[])
        cs=list({c.filename:c for c in cs}.values())
        lh=[]
        if r['artifact_name']:lh+=ln.get(norm(r['artifact_name']),[])
        if r['file_id']:lh+=li.get(r['file_id'].casefold(),[])
        r['library_manifest_evidence']=bool(lh);r['library_hit_count']=len(set(lh));r['physical_match_count']=len(cs)
        if len(cs)==1:
            c=cs[0];r['status']='PHYSICALLY_PRESERVED';r['physical_path']=c.filename;r['physical_size']=c.file_size;used.add(c.filename)
        elif len(cs)>1:r['status']='PHYSICAL_MATCH_AMBIGUOUS';r['physical_path']=' | '.join(sorted(c.filename for c in cs)[:20]);r['physical_size']=''
        else:
            r['physical_path']='';r['physical_size']=''
            if r['library_manifest_evidence']:r['status']='LIBRARY_REFERENCE_ONLY'
            elif r['inline_code_in_message'] and r['artifact_class'] in {'code/firmware','archive/package'}:r['status']='NOT_PHYSICAL_INLINE_CODE_EVIDENCE'
            else:r['status']='REFERENCE_ONLY_NOT_PHYSICAL'
    return used

def writecsv(path,rows,fields):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def esc(x):return html.escape(str(x or ''))
def fmt(n):
    n=float(n)
    for u in ('B','KB','MB','GB','TB'):
        if n<1024 or u=='TB':return f'{n:.1f} {u}' if u!='B' else f'{int(n)} B'
        n/=1024

def report(summary,refs,unref):
    sc=summary['status_counts'];rows=[]
    for r in sorted(refs,key=lambda x:(x['reference_kind']!='sandbox_download',x['status'],x['conversation_date'])):
        cl='ok' if r['status']=='PHYSICALLY_PRESERVED' else 'bad' if r['status']=='REFERENCE_ONLY_NOT_PHYSICAL' else 'warn'
        rows.append(f"<tr><td class='{cl}'>{esc(r['status'])}</td><td>{esc(r['artifact_name'] or r['file_id'])}</td><td>{esc(r['reference_kind'])}</td><td>{esc(r['message_role'])}</td><td>{esc(r['conversation_title')}<br><small>{esc(r['conversation_date')}</small></td><td>{esc(r['physical_path'])}</td><td>{'yes' if r['library_manifest_evidence'] else ''}</td><td>{'yes' if r['inline_code_in_message'] else ''}</td></tr>")
    ur=''.join(f"<tr><td>{esc(x['path'])}</td><td>{esc(x['class'])}</td><td>{fmt(x['size'])}</td></tr>" for x in unref[:5000])
    retur f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChatGPT Artifact Preservation Audit</title><style>body{{margin:0;background:#f4f6fa;color:#1b2533;font:15px/1.45 system-ui}}header{{background:#183153;color:white;padding:28px}}main{{max-width:1400px;margin:auto;padding:20px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}}.card{{background:white;border:1px solid #d9e0e9;border-radius:12px;padding:14px}}.n{{font-size:28px;font-weight:700}}table{{width:100%;border-collapse:collapse;background:white;font-size:13px}}th,td{{padding:8px;border-bottom:1px solid #e2e7ee;vertical-align:top;text-align:left}}th{{position:sticky;top:0;background:#edf2f8}}.ok{{color:#146c2e;font-weight:700}}.warn{{color:#8a5a00;font-weight:700}}.bad{{color:#a52020;font-weight:700}}.note{{background:#fff4ca;padding:12px;border-radius:9px}}small{{color:#68758a}}input{{width:100%;padding:10px;box-sizing:border-box;margin:10px 0}}</style><header><h1>ChatGPT Artifact Preservation Audit</h1><p>Did the finished downloadable artifacts survive, or only the conversations that described them?</p></header><main><p class="note"><b>Important:</b> reference-only means no strong physical match was found in this export. It does not prove permanent loss. Inline code may help reconstruction but is not the exact original package.</p><div class="cards"><div class="card"><div class="n">{summary['conversation_count']:,}</div>conversations</div><div class="card"><div class="n">{summary['reference_count']:,}</div>artifact references</div><div class="card"><div class="n">{sc.get('PHYSICALLY_PRESERVED',0):,}</div>physically preserved</div><div class="card"><div class="n">{sc.get('REFERENCE_ONLY_NOT_PHYSICAL',0):,}</div>reference-only</div><div class="card"><div class="n">{sc.get('NOT_PHYSICAL_INLINE_CODE_EVIDENCE',0):,}</div>inline-code recovery evidence</div><div class="card"><div class="n">{len(unref):,}</div>unreferenced physical artifacts</div></div><h2>Conversation artifact references</h2><input id=q placeholder="Filter..."><div style="overflow:auto;max-height:70vh"><table id=t><thead><tr><th>Status</th><th>Artifact</th><th>Evidence</th><th>Role</th><th>Conversation</th><th>Physical path</th><th>Library</th><th>Inline code</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><details><summary><b>Unreferenced physical artifact-like files ({len(unref):,})</b></summary><p>These physically exist but were not selected as matches. They are not automatically orphans.</p><table><tr><th>Path</th><th>Class</th><th>Size</th></tr>{ur}</table></details><script>const q=document.getElementById('q'),rs=[...document.querySelectorAll('#t tbody tr')];q.oninput=()=>{{let s=q.value.toLowerCase();for(const r of rs)r.style.display=r.innerText.toLowerCase().includes(s)?'':'none'}}</script></main>'''

def audit(zp,out):
    if not zipfile.is_zipfile(zp):raise ValueError('input must be a ChatGPT export ZIP')
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zp,'r',allowZip64=True) as z:
        names=z.namelist();cn=sorted(n for n in names if CONV_RX.search(n))
        if not cn:raise ValueError('no conversations JSON files found')
        infos,pn,pi,pa=physical_index(z);ln,li,lc,lm=lib_index(z,names);refs,st=scan(z,cn);used=resolve(refs,pn,pi,ln,li)
        unref=[{'path':i.filename,'class':artclass(i.filename),'size':i.file_size} for i in pa if i.filename not in used]
    counts=Counter(r['status'] for r in refs)
    summary={'tool':'ChatGPT Artifact Preservation Audit','version':VERSION,'input_zip':str(zp),'conversation_json_files':len(cn),'conversation_count':st['conversations'],'messages_scanned':st['messages'],'messages_with_code_blocks':st['messages_with_code'],'library_manifest_members':lm,'library_record_count_seen':lc,'physical_zip_files':len(infos),'physical_artifact_like_files':len(pa),'reference_count':len(refs),'status_counts':dict(counts),'reference_kind_counts':dict(Counter(r['reference_kind'] for r in refs)),'reference_role_counts':dict(Counter(r['message_role'] for r in refs)),'unreferenced_physical_artifact_count':len(unref)}
    fields=['status','artifact_name','artifact_class','file_id','reference_kind','message_role','conversation_title','conversation_date','conversation_id','message_id','reported_size','mime_type','physical_match_count','physical_path','physical_size','library_manifest_evidence','library_hit_count','inline_code_in_message','evidence']
    writecsv(out/'artifact_audit.csv',refs,fields);writecsv(out/'unreferenced_physical_artifacts.csv',unref,['path','class','size'])
    (out/'artifact_audit.json').write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding='utf-8');(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');(out/'index.html').write_text(report(summary,refs,unref),encoding='utf-8');(out/'README.txt').write_text('Open index.html. Keep this report private: it can expose conversation titles, filenames, IDs, and paths.\n',encoding='utf-8')
    print('\nSummary');print(f"  Conversations: {st['conversations']:,}");print(f"  Artifact references: {len(refs):,}")
    for k,v in counts.most_common():print(f'  {k}: {v:,}')
    print(f"  Report: {out/'index.html'}")

def main():
    p=argparse.ArgumentParser(description='Audit whether downloadable/generated artifacts referenced in ChatGPT conversations physically survive in an export ZIP.');p.add_argument('zipfile',type=Path);p.add_argument('-o','--output',type=Path,default=Path('ChatGPT_Artifact_Audit'));p.add_argument('--version',action='version',version=VERSION);a=p.parse_args()
    try:
        if a.output.exists() and any(a.output.iterdir()):raise ValueError(f'output folder is not empty: {a.output}')
        audit(a.zipfile,a.output);return 0
    except Exception as e:print(f'ERROR: {e}',file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
