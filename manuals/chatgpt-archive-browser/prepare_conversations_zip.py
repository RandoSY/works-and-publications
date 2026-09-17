#!/usr/bin/env python3
"""Create a small conversation-only working ZIP from a ChatGPT data export.

This tool does NOT upload anything and does NOT modify the original export.
It copies only conversations.json or conversations-###.json files into a new ZIP.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

VERSION = "1.1.0"
RX = re.compile(r"(?:^|/)conversations(?:-(\d+))?\.json$", re.IGNORECASE)
CHUNK = 1024 * 1024


def classify_name(name: str):
    m = RX.search(name.replace("\\", "/"))
    if not m:
        return None
    n = m.group(1)
    return (int(n) if n is not None else None, PurePosixPath(name).name)


def first_nonspace(fp) -> str:
    while True:
        block = fp.read(64 * 1024)
        if not block:
            return ""
        if isinstance(block, bytes):
            block = block.decode("utf-8", errors="replace")
        for ch in block:
            if not ch.isspace() and ch != "\ufeff":
                return ch


def choose_members(names):
    found = []
    for name in names:
        c = classify_name(name)
        if c:
            found.append((c[0], name, c[1]))
    numbered = [x for x in found if x[0] is not None]
    plain = [x for x in found if x[0] is None]
    warnings = []
    if numbered:
        selected = sorted(numbered, key=lambda x: (x[0], x[1].lower()))
        if plain:
            warnings.append("Both conversations.json and numbered conversation files were found. Using the numbered set to avoid duplicate conversations.")
    else:
        selected = plain
    if not selected:
        raise ValueError("No conversations.json or conversations-###.json files were found.")

    basenames = [x[2].lower() for x in selected]
    if len(set(basenames)) != len(basenames):
        raise ValueError("Duplicate conversation JSON basenames were found in different folders. Stop and inspect the export manually.")

    nums = [x[0] for x in selected if x[0] is not None]
    if nums:
        expected = list(range(min(nums), max(nums) + 1))
        missing = sorted(set(expected) - set(nums))
        if min(nums) != 0:
            warnings.append(f"The first numbered file is {min(nums):03d}, not 000. This may be legitimate, but verify the export is complete.")
        if missing:
            sample = ", ".join(f"{n:03d}" for n in missing[:20])
            more = " ..." if len(missing) > 20 else ""
            warnings.append(f"Number sequence has gaps: {sample}{more}. Do not assume missing files are harmless.")
    return selected, warnings


def human_bytes(n):
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for u in units:
        if x < 1024 or u == units[-1]:
            return f"{x:.1f} {u}" if u != "B" else f"{int(x)} B"
        x /= 1024


def default_output(source: Path) -> Path:
    base = source.parent if source.is_file() else source.parent
    return base / "ChatGPT_Conversations_Only.zip"


def copy_stream(src, dst):
    while True:
        b = src.read(CHUNK)
        if not b:
            break
        dst.write(b)


def prepare(source: Path, output: Path, overwrite: bool = False):
    source = source.resolve()
    output = output.resolve()
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output}\nUse --overwrite or choose another output name.")
    if source == output:
        raise ValueError("Input and output paths must be different.")

    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source, "r", allowZip64=True) as zin:
            selected, warnings = choose_members(zin.namelist())
            records = []
            output.parent.mkdir(parents=True, exist_ok=True)
            mode = "w"
            with zipfile.ZipFile(output, mode, compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zout:
                for seq, (num, member, basename) in enumerate(selected, 1):
                    info = zin.getinfo(member)
                    print(f"[{seq}/{len(selected)}] copying {basename}  ({human_bytes(info.file_size)})")
                    with zin.open(member, "r") as src:
                        if first_nonspace(src) != "[":
                            raise ValueError(f"{member} does not look like a top-level conversation JSON array.")
                    with zin.open(member, "r") as src, zout.open(basename, "w", force_zip64=True) as dst:
                        copy_stream(src, dst)
                    records.append((basename, info.file_size, member))
                manifest = make_manifest(source.name, records, warnings)
                zout.writestr("CONVERSATION_FILES_MANIFEST.txt", manifest)
    elif source.is_dir():
        candidates = [p for p in source.rglob("*.json") if classify_name(p.relative_to(source).as_posix())]
        rel_names = [p.relative_to(source).as_posix() for p in candidates]
        selected, warnings = choose_members(rel_names)
        by_rel = {p.relative_to(source).as_posix(): p for p in candidates}
        records = []
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zout:
            for seq, (num, rel, basename) in enumerate(selected, 1):
                p = by_rel[rel]
                size = p.stat().st_size
                print(f"[{seq}/{len(selected)}] copying {basename}  ({human_bytes(size)})")
                with p.open("r", encoding="utf-8", errors="replace") as fp:
                    if first_nonspace(fp) != "[":
                        raise ValueError(f"{rel} does not look like a top-level conversation JSON array.")
                with p.open("rb") as src, zout.open(basename, "w", force_zip64=True) as dst:
                    copy_stream(src, dst)
                records.append((basename, size, rel))
            manifest = make_manifest(source.name, records, warnings)
            zout.writestr("CONVERSATION_FILES_MANIFEST.txt", manifest)
    else:
        raise ValueError("Input must be the original ChatGPT export ZIP or an extracted export folder.")

    # Reopen to verify the working ZIP is readable and contains the expected files.
    with zipfile.ZipFile(output, "r", allowZip64=True) as check:
        bad = check.testzip()
        if bad:
            raise ValueError(f"ZIP verification failed at {bad}")
        out_names = set(check.namelist())
        expected_names = {r[0] for r in records}
        if not expected_names.issubset(out_names):
            raise ValueError("ZIP verification failed: one or more conversation files are missing.")

    total = sum(r[1] for r in records)
    print("\nSUCCESS")
    print(f"Conversation JSON files collected: {len(records)}")
    print(f"Uncompressed conversation data:      {human_bytes(total)}")
    print(f"Working ZIP:                          {output}")
    print(f"Working ZIP size:                     {human_bytes(output.stat().st_size)}")
    if warnings:
        print("\nWARNINGS")
        for w in warnings:
            print("- " + w)
    print("\nKeep the original export ZIP unchanged. Use the new conversation-only ZIP as input to the archive browser.")
    return len(records), warnings


def make_manifest(source_name, records, warnings):
    lines = [
        "ChatGPT Conversation-Only Working ZIP",
        "=====================================",
        "",
        f"Source export: {source_name}",
        f"Conversation JSON files: {len(records)}",
        "",
        "This ZIP intentionally contains conversation JSON only.",
        "The original ChatGPT export remains the source of truth for attachments and other account data.",
        "",
        "Files:",
    ]
    for basename, size, original in records:
        lines.append(f"- {basename} | {size} bytes | source member: {original}")
    if warnings:
        lines.extend(["", "Warnings:"] + ["- " + w for w in warnings])
    lines.extend(["", "Do not publish this ZIP. It contains private conversation content.", ""])
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Collect only ChatGPT conversation JSON files into a clean working ZIP.")
    p.add_argument("input", type=Path, help="Original ChatGPT export ZIP or extracted export directory")
    p.add_argument("-o", "--output", type=Path, help="Output ZIP (default: ChatGPT_Conversations_Only.zip beside input)")
    p.add_argument("--overwrite", action="store_true", help="Replace an existing output ZIP")
    p.add_argument("--version", action="version", version=VERSION)
    a = p.parse_args()
    out = a.output or default_output(a.input)
    try:
        prepare(a.input, out, a.overwrite)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())