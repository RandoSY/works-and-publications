#!/usr/bin/env python3
"""ChatGPT Export Spy v1.0.0
Fast structural census of a ChatGPT export ZIP.
Reads ZIP directory metadata only; does not extract or parse conversation contents.
"""
from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

VERSION = "1.0.0"
CONV_RX = re.compile(r"(?:^|/)conversations(?:-(\d+))?\.json$", re.I)

KNOWN_BASENAMES = {
    "library-files.json": "Library manifest",
    "library_files.json": "Library manifest",
    "chat.html": "Chat HTML viewer",
    "user.json": "Account/profile metadata",
    "message_feedback.json": "Feedback metadata",
    "shared_conversations.json": "Shared conversation metadata",
    "shared_conversation.json": "Shared conversation metadata",
    "group_chats.json": "Group chat metadata",
    "model_comparisons.json": "Model comparison metadata",
}

EXT_CLASSES = {
    ".png": "Image asset", ".jpg": "Image asset", ".jpeg": "Image asset", ".gif": "Image asset",
    ".webp": "Image asset", ".bmp": "Image asset", ".tif": "Image asset", ".tiff": "Image asset",
    ".svg": "Image asset", ".heic": "Image asset",
    ".mp3": "Audio asset", ".wav": "Audio asset", ".m4a": "Audio asset", ".ogg": "Audio asset",
    ".flac": "Audio asset", ".aac": "Audio asset",
    ".mp4": "Video asset", ".mov": "Video asset", ".mkv": "Video asset", ".webm": "Video asset",
    ".avi": "Video asset", ".m4v": "Video asset",
    ".pdf": "Document", ".doc": "Document", ".docx": "Document", ".rtf": "Document",
    ".odt": "Document", ".epub": "Document", ".ppt": "Presentation", ".pptx": "Presentation", ".odp": "Presentation",
    ".csv": "Tabular/data file", ".tsv": "Tabular/data file", ".xlsx": "Spreadsheet",
    ".xls": "Spreadsheet", ".ods": "Spreadsheet", ".parquet": "Tabular/data file",
    ".zip": "Nested archive/package", ".7z": "Nested archive/package", ".tar": "Nested archive/package",
    ".gz": "Nested archive/package", ".tgz": "Nested archive/package", ".bz2": "Nested archive/package",
    ".xz": "Nested archive/package", ".rar": "Nested archive/package",
    ".txt": "Text/code file", ".md": "Text/code file", ".py": "Text/code file", ".js": "Text/code file",
    ".ts": "Text/code file", ".html": "Text/code file", ".htm": "Text/code file", ".css": "Text/code file",
    ".java": "Text/code file", ".c": "Text/code file", ".h": "Text/code file", ".cpp": "Text/code file",
    ".hpp": "Text/code file", ".ino": "Text/code file", ".sh": "Text/code file", ".bat": "Text/code file",
    ".ps1": "Text/code file", ".yaml": "Text/code file", ".yml": "Text/code file", ".xml": "Text/code file", ".log": "Text/code file",
}

UNKNOWN_CLASSES = {"Unknown / no extension", "Unknown / unsupported extension"}


def human_size(n: int) -> str:
    x = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or unit == "TB":
            return f"{int(x)} B" if unit == "B" else f"{x:.1f} {unit}"
        x /= 1024
    return f"{x:.1f} TB"


def classify(name: str, is_dir: bool) -> str:
    if is_dir:
        return "Directory entry"
    p = PurePosixPath(name)
    base = p.name.lower()
    if CONV_RX.search(name):
        return "Conversation JSON"
    if base in KNOWN_BASENAMES:
        return KNOWN_BASENAMES[base]
    ext = p.suffix.lower()
    if ext == ".json":
        return "Other JSON metadata"
    if ext in EXT_CLASSES:
        return EXT_CLASSES[ext]
    if not ext:
        return "Unknown / no extension"
    return "Unknown / unsupported extension"


def archive_shape(counts: Counter) -> str:
    total_files = sum(v for k, v in counts.items() if k != "Directory entry")
    conv = counts["Conversation JSON"]
    assets = sum(v for k, v in counts.items() if k.endswith("asset") or k in {
        "Document", "Presentation", "Spreadsheet", "Tabular/data file", "Nested archive/package", "Text/code file"
    })
    metadata = sum(v for k, v in counts.items() if "metadata" in k.lower() or k in {"Library manifest", "Chat HTML viewer"})
    unknown = sum(counts[k] for k in UNKNOWN_CLASSES)
    if total_files and conv == total_files:
        return "Conversation-only working corpus"
    if conv and assets:
        return "Mixed/full export: conversations plus file/media resources"
    if conv and metadata and not assets:
        return "Conversation + metadata export (few/no file assets detected)"
    if assets and not conv:
        return "Asset-heavy archive: resources present, conversation corpus not detected"
    if metadata and not conv and not assets:
        return "Metadata-only or partial export"
    if unknown and not conv and not assets:
        return "Unrecognized archive structure"
    return "Partial/mixed archive"


def conversation_sequence(infos):
    nums = []
    unnumbered = 0
    for i in infos:
        m = CONV_RX.search(i.filename)
        if not m:
            continue
        if m.group(1) is None:
            unnumbered += 1
        else:
            nums.append(int(m.group(1)))
    nums = sorted(set(nums))
    gaps = []
    if nums:
        gaps = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
    return unnumbered, nums, gaps


def top_bucket(name: str) -> str:
    parts = PurePosixPath(name).parts
    return parts[0] if len(parts) > 1 else "[root]"


def compression_name(method: int) -> str:
    return {
        zipfile.ZIP_STORED: "stored",
        zipfile.ZIP_DEFLATED: "deflated",
        getattr(zipfile, "ZIP_BZIP2", -999): "bzip2",
        getattr(zipfile, "ZIP_LZMA", -998): "lzma",
    }.get(method, f"method-{method}")


def make_html(summary, class_rows, top_rows, candidates, duplicates, gaps, all_rows):
    def esc(s): return html.escape(str(s))
    def table(headers, rows):
        head = ''.join(f'<th>{esc(h)}</th>' for h in headers)
        body = ''.join('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>' for r in rows)
        return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
    candidate_rows = [[r['name'], r['class'], human_size(r['size'])] for r in candidates[:500]]
    dup_rows = [[name, count] for name, count in duplicates[:200]]
    gap_text = ', '.join(map(str, gaps[:200])) + (' ...' if len(gaps) > 200 else '') if gaps else 'None detected'
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChatGPT Export Census</title><style>
body{{margin:0;background:#f5f7fb;color:#1d2734;font:15px/1.45 system-ui}}main{{max-width:1100px;margin:auto;padding:24px}}h1,h2{{line-height:1.15}}.hero{{background:#203e78;color:white;padding:26px}}.hero div{{max-width:1100px;margin:auto}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0}}.card{{background:white;border:1px solid #dce3ec;border-radius:12px;padding:14px}}.big{{font-size:1.6rem;font-weight:700}}table{{width:100%;border-collapse:collapse;background:white;margin:10px 0 24px}}th,td{{padding:8px 10px;border-bottom:1px solid #e5e9ef;text-align:left;vertical-align:top}}th{{background:#eef3fa}}code{{background:#eef3fa;padding:2px 5px;border-radius:5px}}.warn{{background:#fff3c4;padding:12px;border-radius:10px}}.ok{{background:#eaf7ee;padding:12px;border-radius:10px}}</style></head><body>
<div class="hero"><div><h1>ChatGPT Export Census</h1><p>Fast structural inventory from ZIP directory metadata only. No conversation content was parsed.</p></div></div><main>
<div class="cards"><div class="card"><div class="big">{summary['members']:,}</div>ZIP members</div><div class="card"><div class="big">{summary['files']:,}</div>files</div><div class="card"><div class="big">{human_size(summary['uncompressed'])}</div>uncompressed</div><div class="card"><div class="big">{summary['unknown']:,}</div>unclassified candidates</div></div>
<h2>Archive shape</h2><p class="ok"><b>{esc(summary['shape'])}</b></p>
<p><b>Input:</b> <code>{esc(summary['input'])}</code><br><b>Compressed ZIP size:</b> {human_size(summary['zip_bytes'])}<br><b>Compression ratio:</b> {summary['ratio']:.1f}×<br><b>Encrypted members:</b> {summary['encrypted']}<br><b>Zero-byte files:</b> {summary['zero_files']}</p>
<h2>Resource classes</h2>{table(['Class','Count','Uncompressed','Compressed'], class_rows)}
<h2>Top-level locations</h2>{table(['Path bucket','Count','Uncompressed'], top_rows)}
<h2>Conversation chunks</h2><p>Unnumbered <code>conversations.json</code>: {summary['unnumbered_conv']}<br>Numbered chunks: {summary['numbered_conv']}<br>First/last number: {esc(summary['conv_range'])}<br>Sequence gaps: {esc(gap_text)}</p>
<h2>Unclassified / orphan candidates</h2><p class="warn">These are <b>not proven orphans</b>. The Spy only knows ZIP names and metadata. Use the Library Audit or a reference-graph scan to determine whether a file is truly unreferenced.</p>
{table(['ZIP member','Classification','Size'], candidate_rows) if candidate_rows else '<p>None.</p>'}
<h2>Duplicate basenames</h2><p>Same filename appearing in more than one ZIP path can be normal, but it is worth knowing about.</p>{table(['Basename','Occurrences'], dup_rows) if dup_rows else '<p>None.</p>'}
<h2>Outputs</h2><p><code>report.txt</code> is the concise summary. <code>members.csv</code> is the complete member inventory.</p>
</main></body></html>'''


def run(zip_path: Path, out_dir: Path):
    if not zip_path.is_file() or not zipfile.is_zipfile(zip_path):
        raise ValueError("Input must be a readable ZIP file")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r", allowZip64=True) as z:
        infos = z.infolist()

    rows = []
    counts = Counter()
    class_sizes = defaultdict(lambda: [0, 0])
    top_counts = Counter()
    top_sizes = Counter()
    basenames = Counter()
    methods = Counter()
    encrypted = 0
    zero_files = 0
    for i in infos:
        is_dir = i.is_dir()
        cls = classify(i.filename, is_dir)
        counts[cls] += 1
        class_sizes[cls][0] += i.file_size
        class_sizes[cls][1] += i.compress_size
        bucket = top_bucket(i.filename)
        top_counts[bucket] += 1
        top_sizes[bucket] += i.file_size
        if not is_dir:
            basenames[PurePosixPath(i.filename).name.lower()] += 1
            if i.file_size == 0:
                zero_files += 1
        methods[compression_name(i.compress_type)] += 1
        if i.flag_bits & 0x1:
            encrypted += 1
        rows.append({
            'name': i.filename, 'class': cls, 'size': i.file_size, 'compressed': i.compress_size,
            'ratio': (i.file_size / i.compress_size) if i.compress_size else None,
            'crc32': f"{i.CRC:08x}", 'compression': compression_name(i.compress_type),
            'encrypted': bool(i.flag_bits & 0x1), 'top_level': bucket,
        })

    files = sum(1 for i in infos if not i.is_dir())
    unc = sum(i.file_size for i in infos)
    comp = sum(i.compress_size for i in infos)
    unknown_rows = [r for r in rows if r['class'] in UNKNOWN_CLASSES]
    duplicates = sorted(((k, v) for k, v in basenames.items() if v > 1), key=lambda x: (-x[1], x[0]))
    unnumbered, nums, gaps = conversation_sequence(infos)
    summary = {
        'input': zip_path.name, 'members': len(infos), 'files': files, 'uncompressed': unc,
        'compressed_members': comp, 'zip_bytes': zip_path.stat().st_size,
        'ratio': (unc / comp) if comp else 0.0, 'unknown': len(unknown_rows), 'encrypted': encrypted,
        'zero_files': zero_files, 'shape': archive_shape(counts), 'unnumbered_conv': unnumbered,
        'numbered_conv': len(nums), 'conv_range': f"{nums[0]:03d}..{nums[-1]:03d}" if nums else "n/a",
    }

    class_rows = [[cls, counts[cls], human_size(class_sizes[cls][0]), human_size(class_sizes[cls][1])]
                  for cls in sorted(counts, key=lambda c: (-counts[c], c))]
    top_rows = [[b, top_counts[b], human_size(top_sizes[b])] for b in sorted(top_counts, key=lambda b: (-top_counts[b], b))]

    csv_path = out_dir / 'members.csv'
    with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['name','class','size','compressed','ratio','crc32','compression','encrypted','top_level'])
        w.writeheader(); w.writerows(rows)

    report = []
    report.append('CHATGPT EXPORT CENSUS')
    report.append('=' * 72)
    report.append(f"Input: {zip_path}")
    report.append(f"Archive shape: {summary['shape']}")
    report.append(f"ZIP members: {len(infos):,}   Files: {files:,}")
    report.append(f"ZIP bytes on disk: {human_size(zip_path.stat().st_size)}")
    report.append(f"Uncompressed member bytes: {human_size(unc)}")
    report.append(f"Compression ratio: {summary['ratio']:.1f}x")
    report.append(f"Encrypted members: {encrypted}   Zero-byte files: {zero_files}")
    report.append('')
    report.append('RESOURCE CLASSES')
    for cls, count, usz, csz in class_rows:
        report.append(f"  {cls:38s} {count:8,d}   {usz:>10s}   compressed {csz:>10s}")
    report.append('')
    report.append('CONVERSATION CHUNKS')
    report.append(f"  unnumbered conversations.json: {unnumbered}")
    report.append(f"  numbered chunks: {len(nums)}")
    report.append(f"  range: {summary['conv_range']}")
    report.append(f"  gaps: {gaps if gaps else 'none detected'}")
    report.append('')
    report.append('UNCLASSIFIED / ORPHAN CANDIDATES')
    report.append('  These are structural candidates only; they are NOT proven semantic orphans.')
    report.append(f"  count: {len(unknown_rows):,}")
    for r in unknown_rows[:200]:
        report.append(f"    {r['name']}   [{r['class']}]   {human_size(r['size'])}")
    if len(unknown_rows) > 200:
        report.append(f"    ... {len(unknown_rows)-200:,} more; see members.csv")
    report.append('')
    report.append('DUPLICATE BASENAMES')
    report.append(f"  count: {len(duplicates):,}")
    for name, count in duplicates[:100]:
        report.append(f"    {count:5d}  {name}")
    if len(duplicates) > 100:
        report.append(f"    ... {len(duplicates)-100:,} more; see members.csv")
    report.append('')
    report.append('COMPRESSION METHODS')
    for name, count in sorted(methods.items()):
        report.append(f"  {name}: {count:,}")
    report.append('')
    report.append('Interpretation rule: Census tells you WHAT IS THERE structurally. Library Audit tells you WHAT IS MISSING relative to Library records.')
    (out_dir / 'report.txt').write_text('\n'.join(report) + '\n', encoding='utf-8')
    (out_dir / 'index.html').write_text(make_html(summary, class_rows, top_rows, unknown_rows, duplicates, gaps, rows), encoding='utf-8')
    return summary


def main():
    ap = argparse.ArgumentParser(description='Fast structural census of a ChatGPT export ZIP. No content parsing.')
    ap.add_argument('zipfile', type=Path, help='Original ChatGPT export ZIP or another ZIP to inspect')
    ap.add_argument('-o','--output', type=Path, default=Path('ChatGPT_Export_Census'), help='Output directory')
    ap.add_argument('--version', action='version', version=VERSION)
    a = ap.parse_args()
    try:
        s = run(a.zipfile, a.output)
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1
    print(f"Archive shape: {s['shape']}")
    print(f"Members: {s['members']:,}; files: {s['files']:,}; uncompressed: {human_size(s['uncompressed'])}")
    print(f"Unclassified/orphan candidates: {s['unknown']:,}")
    print(f"Report: {a.output / 'index.html'}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
