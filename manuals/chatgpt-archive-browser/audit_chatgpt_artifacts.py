#!/usr/bin/env python3
"""ChatGPT Artifact Preservation Audit v1.0.0.

Read-only local audit for ChatGPT export ZIPs. It answers a narrow question:
Which downloadable/generated artifacts referenced by conversations are physically preserved
in the export, represented only by metadata/Library records, or present only as conversation evidence?

Standard library only. Does not extract the archive.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import io
import json
import re
import sys
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

VERSION = "1.0.0"
CHUNK = 1024 * 1024
CONV_RX = re.compile(r"(?:^|/)conversations(?:-\d+)?\.json$", re.I)
LIBRARY_RX = re.compile(r"(?:^|/)library[-_]files\.json$", re.I)
FILE_ID_RX = re.compile(r"\b(?:file|asset)[-_][A-Za-z0-9]{6,}\b", re.I)
SANDBOX_RX = re.compile(r"sandbox:/mnt/data/([^\s\)\]\}\>\"']+)", re.I)
FILE_SERVICE_RX = re.compile(r"file-service://((?:file|asset)[-_][A-Za-z0-9]{6,})", re.I)
CODE_FENCE_RX = re.compile(r"```(?:[A-Za-z0-9_+.#-]+)?\s*\n(.*?)```", re.S)

# Artifact-like extensions: things users commonly mean by "the finished downloadable work".
ARCHIVE_EXT = {'.zip', '.7z', '.tar', '.gz', '.tgz', '.bz2', '.xz'}
CODE_EXT = {
    '.py', '.pyw', '.ino', '.c', '.h', '.cc', '.cpp', '.cxx', '.hpp', '.hh',
    '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.java', '.cs', '.go', '.rs',
    '.sh', '.bash', '.ps1', '.bat', '.cmd', '.html', '.htm', '.css', '.json',
    '.yaml', '.yml', '.toml', '.xml', '.sql', '.asm', '.s', '.forth', '.fs', '.fth',
    '.uf2', '.hex', '.bin', '.elf', '.map', '.cmake', '.mk'
}
DOC_EXT = {'.md', '.txt', '.pdf', '.doc', '.docx', '.rtf', '.odt', '.ppt', '.pptx'}
DATA_EXT = {'.csv', '.tsv', '.xls', '.xlsx', '.ods', '.sqlite', '.db', '.parquet'}
CAD_EXT = {
    '.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_prl', '.sch', '.brd', '.pcb',
    '.gbr', '.drl', '.step', '.stp', '.stl', '.obj', '.fcstd'
}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.tif', '.tiff'}
ALL_ARTIFACT_EXT = ARCHIVE_EXT | CODE_EXT | DOC_EXT | DATA_EXT | CAD_EXT | IMAGE_EXT
# longest first so .kicad_pcb wins over a generic suffix split
EXT_ALT = '|'.join(sorted((re.escape(x) for x in ALL_ARTIFACT_EXT), key=len, reverse=True))
FILENAME_RX = re.compile(r"(?<![\w/\\])([A-Za-z0-9][A-Za-z0-9 _+,.()\[\]{}@#~=-]{0,180}(?:" + EXT_ALT + r"))\b", re.I)

STRUCTURAL_BASENAMES = {
    'chat.html', 'library-files.json', 'library_files.json', 'user.json', 'account.json',
    'shared_conversations.json', 'feedback.json'
}


def fmt_bytes(n: int | None) -> str:
    if n is None:
        return ''
    n = float(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return f"{n:.1f} {unit}" if unit != 'B' else f"{int(n)} B"
        n /= 1024
    return str(n)


def iso_date(ts) -> str:
    try:
        return dt.datetime.fromtimestamp(float(ts), tz=dt.timezone.utc).isoformat()
    except Exception:
        return ''


def norm_name(s: str) -> str:
    s = urllib.parse.unquote(str(s or '')).replace('\\', '/').strip()
    s = PurePosixPath(s).name
    return s.casefold()


def suffix_lower(name: str) -> str:
    low = name.casefold()
    for ext in sorted(ALL_ARTIFACT_EXT, key=len, reverse=True):
        if low.endswith(ext):
            return ext
    return PurePosixPath(low).suffix


def artifact_class(name: str) -> str:
    ext = suffix_lower(name)
    if ext in ARCHIVE_EXT: return 'archive/package'
    if ext in CODE_EXT: return 'code/firmware'
    if ext in CAD_EXT: return 'CAD/PCB/model'
    if ext in DOC_EXT: return 'document'
    if ext in DATA_EXT: return 'data/spreadsheet'
    if ext in IMAGE_EXT: return 'image'
    return 'other'


def is_artifact(name: str) -> bool:
    return suffix_lower(name) in ALL_ARTIFACT_EXT


def extract_text(v) -> str:
    if v is None: return ''
    if isinstance(v, str): return v
    if isinstance(v, (int, float, bool)): return str(v)
    if isinstance(v, list): return '\n'.join(extract_text(x) for x in v if x is not None)
    if isinstance(v, dict):
        if 'parts' in v: return extract_text(v['parts'])
        if v.get('content_type') in {'text', 'input_text', 'output_text'} and 'text' in v:
            return extract_text(v['text'])
        out = []
        for k in ('text', 'caption', 'name', 'title'):
            if k in v and isinstance(v[k], (str, list, dict)):
                out.append(extract_text(v[k]))
        return '\n'.join(x for x in out if x)
    return ''


def iter_array(fp):
    """Incrementally parse a top-level JSON array from a text stream."""
    dec = json.JSONDecoder(); buf = ''; pos = 0; begun = False; eof = False
    while True:
        if pos > 4 * CHUNK:
            buf = buf[pos:]; pos = 0
        while pos < len(buf) and buf[pos].isspace(): pos += 1
        if not begun:
            if pos >= len(buf):
                if eof: raise ValueError('empty JSON')
                c = fp.read(CHUNK); eof = (c == ''); buf += c; continue
            if buf[pos] != '[': raise ValueError('expected top-level JSON array')
            begun = True; pos += 1
        while pos < len(buf) and (buf[pos].isspace() or buf[pos] == ','): pos += 1
        if pos < len(buf) and buf[pos] == ']': return
        if pos >= len(buf):
            if eof: return
            c = fp.read(CHUNK); eof = (c == ''); buf += c; continue
        try:
            obj, end = dec.raw_decode(buf, pos); pos = end; yield obj
        except json.JSONDecodeError:
            if eof: raise
            c = fp.read(CHUNK); eof = (c == ''); buf += c


def active_messages(conv: dict) -> list[dict]:
    mp = conv.get('mapping') or {}; cur = conv.get('current_node'); out = []; seen = set()
    while cur and cur in mp and cur not in seen:
        seen.add(cur); node = mp[cur] or {}; msg = node.get('message')
        if isinstance(msg, dict): out.append(msg)
        cur = node.get('parent')
    if out: return out[::-1]
    msgs = [n.get('message') for n in mp.values() if isinstance(n, dict) and isinstance(n.get('message'), dict)]
    return sorted(msgs, key=lambda m: (m.get('create_time') is None, m.get('create_time') or 0))


def flatten_scalars(v):
    if isinstance(v, dict):
        for x in v.values(): yield from flatten_scalars(x)
    elif isinstance(v, list):
        for x in v: yield from flatten_scalars(x)
    elif isinstance(v, (str, int, float, bool)) and v is not None:
        yield str(v)


def library_indexes(z: zipfile.ZipFile, names: list[str]):
    by_name = defaultdict(list); by_id = defaultdict(list); count = 0; members = [n for n in names if LIBRARY_RX.search(n)]
    for n in members:
        try:
            raw = json.load(io.TextIOWrapper(z.open(n), encoding='utf-8', errors='replace'))
        except Exception:
            continue
        records = raw if isinstance(raw, list) else raw.get('files') if isinstance(raw, dict) and isinstance(raw.get('files'), list) else [raw]
        for i, rec in enumerate(records):
            count += 1
            strings = list(flatten_scalars(rec))
            for s in strings:
                nn = norm_name(s)
                if nn and is_artifact(nn): by_name[nn].append((n, i))
                for fid in FILE_ID_RX.findall(s): by_id[fid.casefold()].append((n, i))
    return by_name, by_id, count, members


def physical_indexes(z: zipfile.ZipFile):
    infos = [i for i in z.infolist() if not i.is_dir()]
    by_name = defaultdict(list); by_id = defaultdict(list)
    artifacts = []
    for i in infos:
        base = PurePosixPath(i.filename).name
        nn = norm_name(base)
        by_name[nn].append(i)
        for fid in FILE_ID_RX.findall(i.filename): by_id[fid.casefold()].append(i)
        if is_artifact(base) and not CONV_RX.search(i.filename) and base.casefold() not in STRUCTURAL_BASENAMES:
            artifacts.append(i)
    return infos, by_name, by_id, artifacts


def add_ref(store, *, conv, msg, kind, name='', file_id='', size=None, mime='', evidence='', confidence='medium', inline_code=False):
    name = urllib.parse.unquote(name or '').strip().strip('`_*.,;:')
    if name:
        name = PurePosixPath(name.replace('\\','/')).name
    if not name and not file_id: return
    if name and not is_artifact(name) and kind not in {'attachment_metadata', 'file_service_pointer'}:
        return
    role = str((msg.get('author') or {}).get('role') or 'unknown')
    key = (str(conv.get('conversation_id') or conv.get('id') or ''), str(msg.get('id') or ''), kind, norm_name(name), file_id.casefold())
    if key in store: return
    store[key] = {
        'conversation_id': str(conv.get('conversation_id') or conv.get('id') or ''),
        'conversation_title': str(conv.get('title') or 'Untitled conversation'),
        'conversation_date': iso_date(conv.get('create_time')),
        'message_id': str(msg.get('id') or ''),
        'message_role': role,
        'reference_kind': kind,
        'confidence': confidence,
        'artifact_name': name,
        'artifact_class': artifact_class(name) if name else 'unknown',
        'file_id': file_id,
        'reported_size': size if isinstance(size, (int,float)) else '',
        'mime_type': mime or '',
        'evidence': evidence[:500],
        'inline_code_in_message': bool(inline_code),
    }


def scan_conversations(z: zipfile.ZipFile, conv_names: list[str]):
    refs = {}
    stats = Counter()
    for idx, n in enumerate(conv_names, 1):
        print(f"[{idx}/{len(conv_names)}] scanning {n}")
        with io.TextIOWrapper(z.open(n), encoding='utf-8', errors='replace') as fp:
            for conv in iter_array(fp):
                stats['conversations'] += 1
                for msg in active_messages(conv):
                    stats['messages'] += 1
                    text = extract_text(msg.get('content') or {})
                    code_blocks = CODE_FENCE_RX.findall(text)
                    inline = bool(code_blocks)
                    if inline: stats['messages_with_code_blocks'] += 1
                    md = msg.get('metadata') or {}
                    attachments = md.get('attachments') or []
                    if isinstance(attachments, list):
                        for a in attachments:
                            if not isinstance(a, dict): continue
                            name = str(a.get('name') or a.get('filename') or '')
                            fid = str(a.get('id') or a.get('file_id') or '')
                          size = a.get('size') or a.get('size_bytes') or a.get('file_token_size') or a.get('fileTokenSize')
                            mime = str(a.get('mime_type') or a.get('mimeType') or '')
                          add_ref(refs, conv=conv, msg=msg, kind='attachment_metadata', name=name, file_id=fid, size=size, mime=mime,
                                        evidence=f"attachment metadata: {name or fid}", confidence='strong', inline_code=inline)
                    sandbox_hits = []
                    for m in SANDBOX_RX.finditer(text):
                        raw = m.group(1).rstrip('.,;:')
                        sandbox_hits.append(norm_name(raw))
                        add_ref(refs, conv=conv, msg=msg, kind='sandbox_download', name=raw,
                                    evidence=f"sandbox:/mnt/data/{raw}", confidence='very strong', inline_code=inline)
                    for m in FILE_SERVICE_RX.finditer(text):
                        add_ref(refs, conv=conv, msg=msg, kind='file_service_pointer', file_id=m.group(1),
                                        evidence=m.group(0), confidence='strong', inline_code=inline)
                    # Generic filename mentions are weaker. If the message already contains a strong
                    # sandbox download link, do not add noisy prose-derived duplicates.
                    if not sandbox_hits:
                        for m in FILENAME_RX.finditer(text):
                            candidate = m.group(1).strip().strip('[](){}<>')
                            # Trim common prose prefixes while preserving ordinary spaced filenames.
                            candidate = re.sub(r'(?:download|file|attached|attachment|here is|here are|open)\s+', '', candidate, flags=re.I)
                            add_ref(refs, comv=conv, msg=msg, kind='filename_mention', name=candidate,
                                        eidence=candidate, confidence='weak', inline_code=inline)
    return list(refs.values()), stats


def resolve_refs(refs, physical_by_name, physical_by_id, library_by_name, library_by_id):
    selected_paths = set()
    for r in refs: 
        candidates = []
        if r['artifact_name']:
            candidates.extend(physical_by_name.get(norm_name(r['artifact_name']), []))
        if r['file_id']:
            candidates.extend(physical_by_id.get(r['file_id'].casefold(), []))
        # de-duplicate paths
        uniq = {c.filename: c for c in candidates}
        candidates = list(uniq.values())
        lib_hits = []
        if r['artifact_name']: lib_hits.extend(library_by_name.get(norm_name(r['artifact_name']), []))
        if r['file_id']: lib_hits.extend(library_by_id.get(r['file_id'].casefold(), []))
        r['library_manifest_evidence'] = bool(lib_hits)
        r['library_hit_count'] = len(set(lib_hits))
        r['physical_match_count'] = len(candidates)
        if len(candidates) == 1:
            c = candidates[0]
            r['status'] = 'PHYSICALLY_PRESERVED'
            r['physical_path'] = c.filename
            r['physical_size'] = c.file_size
            selected_paths.add(c.filename)
        elif len(candidates) > 1:
            r["status"] = 'PHYSICAL_MATCH_AMBIGUOUS'
            r['physical_path'] = ' | '.join(sorted(c.filename for c in candidates)[:20])
            r['physical_size'] = ''
        else:
            r["physical_path"] = ''
            r["physical_size"] = ''
            if r['library_manifest_evidence']:
                r["status"] = 'LIBRARY_REFERENCE_ONLY'
            elif r['inline_code_in_message'] and r['artifact_class'] in {'code/firmware', 'archive/package'}:
                r["status"] = 'NOT_PHYSICAL_INLINE_CODE_EVIDENCE'
            else:
                r["status"] = 'REFERENCE_ONLY_NOT_PHYSICAL'
    return selected_paths


def priority(r):
    # Strongest, most artifact-like evidence first.
    k = {'sandbox_download': 0, 'attachment_metadata': 1, 'file_service_pointer': 2, 'filename_mention': 3}.get(r['reference_kind'], 9)
    s = {'REFERENCE_ONLY_NOT_PHYSICAL': 0, 'LIBRARY_REFERENCE_ONLY': 1, 'NOT_PHYSICAL_INLINE_CODE_EVIDENCE': 2,
         'PHYSICAL_MATCH_AMBIGUOUS': 3, 'PHYSICALLY_PRESERVED': 4}.get(r.get('status'), 9)
    return (k, s, r.get('conversation_date',''), r.get('artifact_name',''))


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)


def h(s): return html.escape(str(s or ''))


def build_html(summary, refs, unref):
    status_counts = summary['status_counts']; kind_counts = summary['reference_kind_counts']
    rows = []
    for r in sorted(refs, key=priority):
        cls = 'ok' if r['status']=='PHYSICALLY_PRESERVED' else 'warn' if r['status'] in {'PHYSICAL_MATCH_AMBIGUOUS','NOT_PHYSICAL_INLINE_CODE_EVIDENCE','LIBRARY_REFERENCE_ONLY'} else 'bad'
        rows.append(f"<tr><td class='{cls}'>{h(r['status'])}</td><td>{h(r['artifact_name'] or r['file_id'])}</td><td>{h(r['reference_kind'])}</td><td>{h(r['message_role'])}</td><td>{h(r['conversation_title')}<br><small>{h(r['conversation_date'])}</small></td><td>{h(r['physical_path'])}</td><td>{'yes' if r['library_manifest_evidence'] else ''}</td><td>{'yes' if r['inline_code_in_message'] else ''}</td></tr>")
    unrows = ''.join(f"<tr><td>{h(x['path'])}</td><td>{h(x['class'])}</td><td>{h(fmt_bytes(x['size']))}</td></tr>" for x in unref[:5000])
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChatGPT Artifact Preservation Audit</title><style>
body{{margin:0;background:#f4f6fa;color:#1b2533;font:15px/1.45 system-ui}}.hero{{background:#183153;color:#fff;padding:28px}}main{{max-width:1400px;margin:auto;padding:20px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}}.card{{background:#fff;morder:1px solid #d9e0e9;border-radius:12px;padding:14px}}.n{{font-size:28px;font-weight:700}}table{{width:100%;border-collapse:collapse;background:#fff;font-size:13px}}th,td{{padding:8px;border-bottom:1px solid #e2e7ee;vertical-align:top;text-align:left}}th{{position:sticky;top:0;background:#edf2f8}}.ok{{color:#146c2e;font-weight:700}}.warn{{color:#8a5a00;font-weight:700}}.bad{{color:#a52020;font-weight:700}}code{{background:#eef2f7;padding:2px 5px;border-radius:5px}}.note{{background:#fff4ca;padding:12px;border-radius:9px}}small{{color:#68758a}}details{{margin:18px 0}}input{{width:100%;padding:10px;box-sizing:border-box;margin:10px 0}}</style></head><body>
<div class="hero"><h1>ChatGPT Artifact Preservation Audit</h1><p>Did the finished downloadable artifacts survive, or only the conversations that described them?</p></div><main>
<p class="note"><b>Interpret carefully:</b> “reference only” means no matching physical ZIP member was found by this audit. It does not prove permanent loss. Inline code evidence can aid reconstruction, but it is not equivalent to preserving the exact original package.</p>
<div class="cards">
<div class="card"><div class="n">{summary['conversation_count']:,}</div>conversations scanned</div>
<div class="card"><div class="n">{summary['reference_count']:,}</div>artifact references</div>
<div class="card"><div class="n">{status_counts.get('PHYSICALLY_PRESERVED',0):,}</div>physically preserved refs</div>
<div class="card"><div class="n">{status_counts.get('REFERENCE_ONLY_NOT_PHYSICAL',0):,}</div>reference-only refs</div>
<div class="card"><div class="n">{status_counts.get('NOT_PHYSICAL_INLINE_CODE_EVIDENCE',0):,}</div>missing but inline-code evidence</div>
<div class="card"><div class="n">{len(unref):,}</div>unreferenced physical artifacts</div>
</div>
<h2>Artifact references from conversations</h2><input id="q" placeholder="Filter table by filename, conversation, status, path..."><div style="overflow:auto;max-height:70vh"><table id="t"><thead><tr><th>Status</th><th>Artifact</th><th>Evidence kind</th><th>Role</th><th>Conversation</th><th>Physical path</th><th>Library</th><th>Inline code</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<details><summary><b>Unreferenced physical artifact-like files ({len(unref):,})</b></summary><p>These files physically exist in the export but were not selected as a match for any discovered conversation reference. They are not automatically orphans.</p><div style="overflow:auto;max-height:50vh"><table><tr><th>Path</th><th>Class</th><th>Size</th></tr>{unrows}</table></div></details>
<h2>How to read the statuses</h2><p><b>PHYSICALLY_PRESERVED</b>: a physical ZIP member strongly matched by filename or file ID. <b>LIBRARY_REFERENCE_ONLY</b>: the Library manifest appears to know the artifact, but no matching physical member was found. <b>NOT_PHYSICAL_INLINE_CODE_EVIDENCE</b>: no physical artifact was found, but code blocks exist in the same message and may help reconstruction. <b>REFERENCE_ONLY_NOT_PHYSICAL</b>: the conversation references an artifact but this export contains no strong physical match. <b>PHYSICAL_MATCH_AMBIGUOUS</b>: multiple equally plausible physical files exist.</p>
<script>const q=document.getElementById('q'),rows=[...document.querySelectorAll('#t tbody tr')];q.oninput=()=>{{let s=q.value.toLowerCase();for(const r of rows)r.style.display=r.innerText.toLowerCase().includes(s)?'':'none';}};</script>
</main></body></html>'''


def audit(zip_path: Path, out: Path):
    if not zipfile.is_zipfile(zip_path): raise ValueError('input must be a ChatGPT export ZIP')
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r', allowZip64=True) as z:
        names = z.namelist()
        conv_names = sorted(n for n in names if CONV_RX.search(n))
        if not conv_names: raise ValueError('no conversations JSON files found in this ZIP')
        infos, phys_name, phys_id, physical_artifacts = physical_indexes(z)
        lib_name, lib_id, lib_count, lib_members = library_indexes(z, names)
        refs, scan_stats = scan_conversations(z, conv_names)
        selected = resolve_refs(refs, phys_name, phys_id, lib_name, lib_id)
        unref = [{'path': i.filename, 'class': artifact_class(i.filename), 'size': i.file_size}
                 for i in physical_artifacts if i.filename not in selected]
    status_counts = Counter(r['status'] for r in refs)
    kind_counts = Counter(r['reference_kind'] for r in refs)
    role_counts = Counter(r['message_role'] for r in refs)
    summary = {
        'tool': 'ChatGPT Artifact Preservation Audit', 'version': VERSION,
        'input_zip': str(zip_path), 'zip_bytes': zip_path.stat().st_size,
        'conversation_json_files': len(conv_names), 'conversation_count': scan_stats['conversations'],
        'messages_scanned': scan_stats['messages'], 'messages_with_code_blocks': scan_stats['messages_with_code_blocks'],
        'library_manifest_members': lib_members, 'library_record_count_seen': lib_count,
        'physical_zip_files': len(infos), 'physical_artifact_like_files': len(physical_artifacts),
        'reference_count': len(refs), 'status_counts': dict(status_counts),
        'reference_kind_counts': dict(kind_counts), 'reference_role_counts': dict(role_counts),
        'unreferenced_physical_artifact_count': len(unref),
        'interpretation_note': 'Reference-only is evidence that no strong physical match was found in this export; it is not proof of permanent loss.'
    }
    fields = ['status','artifact_name','artifact_class','file_id','reference_kind','confidence','message_role','conversation_title','conversation_date','conversation_id','message_id','reported_size','mime_type','physical_match_count','physical_path','physical_size','library_manifest_evidence','library_hit_count','inline_code_in_message','evidence']
    write_csv(out/'artifact_audit.csv', sorted(refs, key=priority), fields)
    write_csv(out/'unreferenced_physical_artifacts.csv', unref, ['path','class','size'])
    (out/'artifact_audit.json').write_text(json.dumps(refs, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'index.html').write_text(build_html(summary, refs, unref), encoding='utf-8')
    (out/'README.txt').write_text('Open index.html. Keep this report private: it can expose conversation titles, filenames, IDs, and paths.\n', encoding='utf-8')
    print('\nSummary')
    print(f"  Conversations: {summary['conversation_count']:,}")
    print(f"  Artifact references: {len(refs):,}")
    for k,v in status_counts.most_common(): print(f"  {k}: {v:,}")
    print(f"  Physical artifact-like files: {len(physical_artifacts):,}")
    print(f"  Unreferenced physical artifact-like files: {len(unref):,}")
    print(f"  Report: {out/'index.html'}")


def main():
    p = argparse.ArgumentParser(description='Audit whether downloadable/generated artifacts referenced in ChatGPT conversations physically survive in an export ZIP.')
    p.add_argument('zipfile', type=Path)
    p.add_argument('-o','--output', type=Path, default=Path('ChatGPT_Artifact_Audit'))
    p.add_argument('--version', action='version', version=VERSION)
    a = p.parse_args()
    try:
        if a.output.exists() and any(a.output.iterdir()):
            print(f"ERROR: output folder already exists and is not empty: {a.output}", file=sys.stderr); return 2
        audit(a.zipfile, a.output); return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr); return 1

if __name__ == '__main__': raise SystemExit(main())
