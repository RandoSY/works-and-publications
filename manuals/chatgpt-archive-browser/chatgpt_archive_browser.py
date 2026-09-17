#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, html, io, json, re, shutil, sys, zipfile
from pathlib import Path

VERSION='1.1.0'; CHUNK=1024*1024
RX=re.compile(r'(?:^|/)conversations(?:-\d+)?\.json$',re.I)
TOPICS={
'Programming & Software':'python javascript typescript java c++ code coding program script api git github linux windows database sql debug',
'Electronics & Hardware':'arduino esp32 raspberry pi micro:bit microbit microcontroller sensor circuit pcb bluetooth ble serial uart i2c spi firmware robot',
'AI & Data':'chatgpt openai artificial intelligence machine learning neural llm model dataset prompt',
'Science & Math':'physics chemistry biology geology astronomy science math mathematics equation calculus statistics experiment',
'Education & Learning':'student teacher classroom curriculum lesson education learning school teach worksheet course',
'Health & Fitness':'health exercise fitness doctor medical medicine sleep gait walking diet calorie',
'Writing & Creative':'poem poetry story essay rewrite edit writing novel script comic lyrics speech',
'History & Humanities':'history historical philosophy shakespeare war ancient medieval literature religion culture',
'Food & Cooking':'recipe cook cooking food bake kitchen meal coffee tea restaurant',
'Travel & Places':'travel trip hotel flight vacation visit tour airport destination',
'Finance & Business':'stock finance financial business market investment budget price cost retirement tax',
'Home & Practical':'garage home repair appliance garden house clean storage automobile',
'Personal Reflection':'life remember memory meaning feel feeling reflection enough future past'}

def text(v):
    if v is None:return ''
    if isinstance(v,str):return v
    if isinstance(v,(int,float,bool)):return str(v)
    if isinstance(v,list):return '\n'.join(filter(None,(text(x) for x in v)))
    if isinstance(v,dict):
        for k in ('text','content','caption','name','title'):
            if k in v and text(v[k]):return text(v[k])
        return '[non-text content: %s]'%(v.get('content_type') or v.get('type') or 'unknown')
    return str(v)

def msgtext(m):
    c=m.get('content') or {}
    return text(c.get('parts') if isinstance(c,dict) and 'parts' in c else c)

def active(conv):
    mp=conv.get('mapping') or {}; cur=conv.get('current_node'); out=[]; seen=set()
    while cur and cur in mp and cur not in seen:
        seen.add(cur); n=mp[cur] or {}; m=n.get('message')
        if isinstance(m,dict):out.append(m)
        cur=n.get('parent')
    if out:return out[::-1]
    out=[n.get('message') for n in mp.values() if isinstance(n,dict) and isinstance(n.get('message'),dict)]
    return sorted(out,key=lambda m:(m.get('create_time') is None,m.get('create_time') or 0))

def localdate(ts):
    try:return dt.datetime.fromtimestamp(float(ts),tz=dt.timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M %Z')
    except:return 'Unknown date'

def isotime(ts):
    try:return dt.datetime.fromtimestamp(float(ts),tz=dt.timezone.utc).isoformat()
    except:return ''

def words(s):return len(re.findall(r'\b\w+\b',s,re.U))
def safeid(s):return re.sub(r'[^A-Za-z0-9._-]+','_',s or 'conversation')[:160]

def topic(s):
    s=' '+s.lower()+' '; best=('General / Other',0)
    for name,kw in TOPICS.items():
        score=sum(1 for w in kw.split() if w in s)
        if score>best[1]:best=(name,score)
    return best[0]

def iter_array(fp):
    dec=json.JSONDecoder(); buf=''; pos=0; begun=False; eof=False
    while True:
        if pos>4*CHUNK:buf=buf[pos:];pos=0
        while pos<len(buf) and buf[pos].isspace():pos+=1
        if not begun:
            if pos>=len(buf):
                if eof:raise ValueError('empty JSON')
                c=fp.read(CHUNK); eof=(c==''); buf+=c; continue
            if buf[pos]!='[':raise ValueError('expected top-level JSON array')
            begun=True;pos+=1
        while pos<len(buf) and (buf[pos].isspace() or buf[pos]==','):pos+=1
        if pos<len(buf) and buf[pos]==']':return
        if pos>=len(buf):
            if eof:return
            c=fp.read(CHUNK); eof=(c==''); buf+=c; continue
        try:o,end=dec.raw_decode(buf,pos);pos=end;yield o
        except json.JSONDecodeError:
            if eof:raise
            c=fp.read(CHUNK); eof=(c==''); buf+=c

class Source:
    def __init__(self,p):self.p=Path(p);self.z=None;self.names=[]
    def __enter__(self):
        if self.p.is_dir():self.names=sorted(x.relative_to(self.p).as_posix() for x in self.p.rglob('*.json') if RX.search(x.relative_to(self.p).as_posix()))
        elif zipfile.is_zipfile(self.p):self.z=zipfile.ZipFile(self.p,'r',allowZip64=True);self.names=sorted(n for n in self.z.namelist() if RX.search(n))
        elif self.p.is_file() and self.p.suffix.lower()=='.json':self.names=[self.p.name]
        else:raise ValueError('input must be an export ZIP, extracted directory, or conversation JSON')
        if not self.names:raise ValueError('no conversations JSON files found')
        return self
    def __exit__(self,*_):
        if self.z:self.z.close()
    def open(self,n):
        if self.z:return io.TextIOWrapper(self.z.open(n),encoding='utf-8',errors='replace')
        return open((self.p/n) if self.p.is_dir() else self.p,encoding='utf-8',errors='replace')

def metadata(c,index_chars):
    ms=active(c); title=text(c.get('title')).strip() or 'Untitled conversation'; cid=text(c.get('conversation_id') or c.get('id')).strip() or safeid(title)
    first=''; users=[]; models=[]; wc=0
    for m in ms:
        role=text((m.get('author') or {}).get('role')); t=msgtext(m).strip(); wc+=words(t)
        if role=='user' and t:
            if not first:first=t
            if sum(map(len,users))<index_chars:users.append(t)
        model=text((m.get('metadata') or {}).get('model_slug')).strip()
        if model and model not in models:models.append(model)
    d=text(c.get('default_model_slug')).strip()
    if d and d not in models:models.insert(0,d)
    search=('\n'.join([title]+users))[:index_chars]; ct=c.get('create_time')
    return {'id':cid,'file':'conversations/'+safeid(cid)+'.html','title':title,'create_time':float(ct) if isinstance(ct,(int,float)) else None,'date':localdate(ct),'iso':isotime(ct),'first_user':first[:700],'message_count':len(ms),'word_count':wc,'models':models,'topic':topic(search),'search':search},ms

def one_message(m):
    role=text((m.get('author') or {}).get('role')).strip() or 'unknown'; body=html.escape(msgtext(m).strip()).replace('\n','<br>') or '<em>[No textual content]</em>'
    model=text((m.get('metadata') or {}).get('model_slug')).strip(); meta=localdate(m.get('create_time'))+(' · '+model if model else '')
    return f'<article class="msg {html.escape(role)}"><header><b>{html.escape(role.title())}</b><span>{html.escape(meta)}</span></header><div>{body}</div></article>'

def page(meta,ms):
    model=', '.join(meta['models']) or 'unknown'
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(meta['title'])}</title><style>body{{margin:0;background:#f5f7fb;color:#1d2734;font:16px/1.55 system-ui}}nav,main{{max-width:1000px;margin:auto;padding:14px 18px}}nav{{display:flex;gap:12px;position:sticky;top:0;background:#fffffff2;border-bottom:1px solid #dce3ec}}nav .s{{flex:1}}a{{color:#2457d6;text-decoration:none}}h1{{line-height:1.15}}.meta{{color:#68758a}}.msg{{background:#fff;border:1px solid #dce3ec;border-radius:12px;margin:14px 0;overflow:hidden}}.msg.user{{background:#edf5ff}}.msg header{{padding:9px 14px;border-bottom:1px solid #dce3ec;display:flex;justify-content:space-between;color:#68758a;font-size:13px}}.msg header b{{color:#1d2734}}.msg>div{{padding:15px;overflow-wrap:anywhere}}</style></head><body><nav><a href="../index.html">← Index</a><span class="s"></span>@@PREV@@ <b>@@SEQ@@</b> @@NEXT@@</nav><main><h1>{html.escape(meta['title'])}</h1><p class="meta">{html.escape(meta['date'])} · {meta['message_count']} messages · {meta['word_count']:,} words · {html.escape(model)} · {html.escape(meta['topic'])}</p>{''.join(one_message(m) for m in ms)}</main></body></html>'''

def index_html(cat,title):
    payload=json.dumps(cat,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>body{{margin:0;background:#f4f6fa;color:#1b2533;font:15px/1.45 system-ui}}.wrap{{max-width:1200px;margin:auto;padding:0 18px}}.hero{{background:#203e78;color:#fff;padding:28px 0}}.hero p{{color:#dce7ff}}.warn{{background:#fff3c4;color:#4d421e;padding:9px;border-radius:8px}}.controls{{display:grid;grid-template-columns:2fr repeat(3,1fr);gap:8px;margin:18px 0}}input,select{{padding:10px;border:1px solid #cbd4df;border-radius:8px;font:inherit}}.card{{background:#fff;border:1px solid #dce3ec;border-radius:11px;padding:13px 15px;margin:9px 0}}a{{color:#2457d6;text-decoration:none}}.meta{{color:#68758a;font-size:13px}}.pager{{display:flex;gap:10px;justify-content:center;padding:18px}}button{{padding:8px 12px}}@media(max-width:800px){{.controls{{grid-template-columns:1fr 1fr}}.controls input{{grid-column:1/-1}}}}</style></head><body><div class="hero"><div class="wrap"><h1>{html.escape(title)}</h1><p>Private, offline, chronological browser generated from a ChatGPT export.</p><p class="warn"><b>Privacy:</b> this site contains your conversation text. Keep it local unless you deliberately choose to publish it.</p></div></div><main class="wrap"><div class="controls"><input id="q" placeholder="Search titles and indexed user text"><select id="year"><option value="">All years</option></select><select id="topic"><option value="">All topics</option></select><select id="sort"><option value="old">Oldest first</option><option value="new">Newest first</option><option value="title">Title A–Z</option><option value="long">Longest first</option></select></div><p id="count"></p><section id="out"></section><div class="pager"><button id="prev">Previous</button><span id="pg"></span><button id="next">Next</button></div></main><script id="catalog" type="application/json">{payload}</script><script>const A=JSON.parse(document.getElementById('catalog').textContent),$=x=>document.getElementById(x),esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));let F=[],P=0,N=100;function uniq(a){{return[...new Set(a.filter(Boolean))].sort()}}for(const y of uniq(A.map(x=>x.iso?.slice(0,4))))$('year').insertAdjacentHTML('beforeend',`<option>${{y}}</option>`);for(const t of uniq(A.map(x=>x.topic)))$('topic').insertAdjacentHTML('beforeend',`<option>${{esc(t)}}</option>`);function go(){{let q=$('q').value.toLowerCase(),y=$('year').value,t=$('topic').value,s=$('sort').value;F=A.filter(x=>(!q||(x.title+' '+x.search).toLowerCase().includes(q))&&(!y||x.iso?.startsWith(y))&&(!t||x.topic==t));F.sort((a,b)=>s=='new'?(b.create_time||0)-(a.create_time||0):s=='title'?a.title.localeCompare(b.title):s=='long'?b.word_count-a.word_count:(a.create_time||0)-(b.create_time||0));P=0;draw()}}function draw(){{let a=P*N,b=Math.min(a+N,F.length);$('count').textContent=`${{F.length.toLocaleString()}} conversations`; $('out').innerHTML=F.slice(a,b).map(x=>`<article class="card"><h2><a href="${{esc(x.file)}}">#${{x.seq}} — ${{esc(x.title)}}</a></h2><div class="meta">${{esc(x.date)}} · ${{x.message_count}} messages · ${{x.word_count.toLocaleString()}} words · ${{esc(x.models.join(', ')||'unknown model')}} · ${{esc(x.topic)}}</div><p>${{esc(x.first_user||'[No user-text preview]')}}</p></article>`).join('')||'<div class="card">No matches.</div>';$('pg').textContent=`Page ${{P+1}} of ${{Math.max(1,Math.ceil(F.length/N))}}`;$('prev').disabled=P==0;$('next').disabled=(P+1)*N>=F.length}}for(const id of ['q','year','topic','sort'])$(id).addEventListener(id=='q'?'input':'change',go);$('prev').onclick=()=>{{if(P){{P--;draw();scrollTo(0,0)}}}};$('next').onclick=()=>{{if((P+1)*N<F.length){{P++;draw();scrollTo(0,0)}}}};go();</script></body></html>'''

def patch(path,seq,total,prev,next):
    s=path.read_text(encoding='utf-8'); p=f'<a href="../{html.escape(prev)}">← Previous</a>' if prev else ''; n=f'<a href="../{html.escape(next)}">Next →</a>' if next else ''
    path.write_text(s.replace('@@SEQ@@',f'{seq:,} / {total:,}').replace('@@PREV@@',p).replace('@@NEXT@@',n),encoding='utf-8')

def build(inp,out,title,index_chars,limit,overwrite):
    out=Path(out)
    if out.exists():
        if not overwrite:raise FileExistsError(f'{out} exists; use --overwrite')
        shutil.rmtree(out)
    (out/'conversations').mkdir(parents=True)
    cat=[]; done=0
    with Source(inp) as src:
        print(f'Found {len(src.names)} conversation JSON file(s).')
        for i,n in enumerate(src.names,1):
            print(f'[{i}/{len(src.names)}] {n}')
            with src.open(n) as fp:
                for c in iter_array(fp):
                    m,ms=metadata(c,index_chars); (out/m['file']).write_text(page(m,ms),encoding='utf-8');cat.append(m);done+=1
                    if done%250==0:print(f'  {done:,} conversations')
                    if limit and done>=limit:break
            if limit and done>=limit:break
    cat.sort(key=lambda x:(x['create_time'] is None,x['create_time'] or float('inf'),x['title'].lower()))
    for i,m in enumerate(cat):m['seq']=i+1
    for i,m in enumerate(cat):patch(out/m['file'],i+1,len(cat),cat[i-1]['file'] if i else None,cat[i+1]['file'] if i+1<len(cat) else None)
    (out/'catalog.json').write_text(json.dumps(cat,ensure_ascii=False,indent=2),encoding='utf-8');(out/'index.html').write_text(index_html(cat,title),encoding='utf-8');(out/'README.txt').write_text('Open index.html in a browser. Keep this generated archive private unless you intentionally choose otherwise.\n',encoding='utf-8')
    print(f'Done: {len(cat):,} conversations -> {out}')

def main():
    p=argparse.ArgumentParser(description='Build a private offline HTML browser from a ChatGPT data export.');p.add_argument('input',type=Path);p.add_argument('-o','--output',type=Path,default=Path('ChatGPT_Archive_Browser'));p.add_argument('--title',default='ChatGPT Archive Browser');p.add_argument('--index-chars',type=int,default=6000);p.add_argument('--limit',type=int);p.add_argument('--overwrite',action='store_true');p.add_argument('--version',action='version',version=VERSION);a=p.parse_args()
    try:build(a.input,a.output,a.title,max(0,a.index_chars),a.limit,a.overwrite)
    except Exception as e:print('ERROR:',e,file=sys.stderr);return 1
    return 0
if __name__=='__main__':raise SystemExit(main())