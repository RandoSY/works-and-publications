# ChatGPT Export Spy — Fast Archive Census

The Export Spy is **Layer 0** of the ChatGPT Archive Toolkit.

Use it before the Conversation Browser or Library Audit when you first receive a large ChatGPT export and simply want to know:

- What kinds of files are in this ZIP?
- How many of each kind?
- How large are they?
- Are the numbered conversation JSON chunks complete?
- Is `library-files.json` present?
- Are there images, documents, audio, video, nested ZIPs, or other resources?
- Are there unknown/unclassified members that deserve investigation?

The Spy is intentionally shallow and fast. It reads the ZIP **central directory only**. It does not extract the archive and does not parse conversation text.

## Windows: easiest use

Put these two files together:

- `chatgpt_export_spy.py`
- `spy_windows.bat`

Then drag the **original ChatGPT export ZIP** onto `spy_windows.bat`.

It creates:

```text
ChatGPT_Export_Census/
    index.html
    report.txt
    members.csv
```

Open `index.html` for the dashboard.

## What it classifies

The census groups ZIP members into broad structural classes such as:

- Conversation JSON
- Library manifest
- account/profile and other JSON metadata
- images
- audio
- video
- documents and PDFs
- presentations
- spreadsheets/data
- nested archives/packages
- text/code
- unknown or unsupported extensions

It also reports:

- ZIP member count
- compressed and uncompressed size
- compression ratio
- encrypted members
- zero-byte files
- top-level ZIP path buckets
- numbered conversation chunk range and gaps
- duplicate basenames
- unclassified/orphan candidates

## Important: “orphan candidate” does not mean “proven orphan”

The Spy only sees filenames, paths, extensions, sizes, ZIP metadata, and CRC values.

A file is an **orphan candidate** when its structural class is unknown or unsupported. That is a reason to inspect it, not proof that nothing references it.

Use the deeper **Library Audit** to answer whether Library records have corresponding physical files and whether file relationships can actually be established.

## The three layers

```text
Layer 0 — Export Spy
    What is physically in this ZIP?

Layer 1 — Conversation Browser + Library Audit
    What conversations exist?
    Which Library records/files match or appear missing?

Layer 2 — AI / Project Atlas
    What does the corpus mean?
    How did ideas and projects evolve?
```

## Command line

```bash
python chatgpt_export_spy.py "chatgpt-export.zip" -o ChatGPT_Export_Census
```

No third-party Python packages are required.

## Why this tool exists

Before analyzing a multi-gigabyte export, establish its **shape**.

A one-minute structural census can prevent hours of working on the wrong ZIP, assuming missing resources are present, confusing a conversation-only working archive with a full export, or overlooking unknown file classes.

The Spy answers the first archival question:

> **What, physically, do I have?**
