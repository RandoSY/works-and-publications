# ChatGPT Artifact Preservation Audit

## The question this tool answers

A conversation can survive while the **finished downloadable artifact** does not.

That distinction matters after hours of work producing things such as:

- Arduino projects (`.ino`, `.cpp`, `.h`)
- MicroPython and CircuitPython programs (`.py`)
- complete project ZIPs
- KiCad projects and PCB files
- firmware images (`.uf2`, `.hex`, `.bin`)
- generated PDFs, DOCX, spreadsheets, data files, and manuals

The **Artifact Preservation Audit** asks:

> When a ChatGPT conversation says a downloadable artifact existed, is that artifact physically present in the export, represented only by Library metadata, or absent as a physical file even though the conversation survives?

This is deliberately separate from the other tools in the ChatGPT Archive Toolkit.

## Where this fits

```text
0. Export Spy
   What is physically inside this ZIP at all?

1. Conversation Browser
   What conversations exist and what do they say?

2. Library Audit
   Does library-files.json match physical exported files?

3. Artifact Preservation Audit
   Did the finished downloadable work referenced by conversations survive?

4. AI / Project Atlas
   What does the body of work mean?
```

## Use the ORIGINAL FULL export ZIP

Run this tool against the original ChatGPT export ZIP.

Do **not** run it against `ChatGPT_Conversations_Only.zip` if your goal is to determine whether generated artifacts were preserved. The conversation-only ZIP intentionally removes non-conversation files.

## Easiest Windows procedure

Put these two files together:

- `audit_chatgpt_artifacts.py`
- `audit_artifacts_windows.bat`

Then:

1. Keep your original ChatGPT export ZIP unchanged.
2. Drag that ZIP onto `audit_artifacts_windows.bat`.
3. The utility scans the conversation JSON and ZIP directory without extracting the archive.
4. It creates a folder named `ChatGPT_Artifact_Audit` next to the export.
5. It opens `ChatGPT_Artifact_Audit\index.html`.

Python 3.9 or newer is required. No third-party packages are required.

## What it looks for

The audit finds several kinds of evidence.

### Strong generated-download evidence

A conversation containing a link such as:

```text
sandbox:/mnt/data/MyProject.zip
```

is strong evidence that a downloadable artifact was generated at that point in the conversation.

### Attachment metadata

Conversation JSON can also preserve attachment records containing fields such as filename, file ID, MIME type, and size.

### File-service references

Some conversation records contain `file-service://file-...` identifiers even when the physical asset is not included in the ZIP.

### Ordinary filename mentions

The tool also recognizes artifact-like filenames in conversation text, but labels these as weak evidence. Mentioning `example.py` is not the same thing as proving that ChatGPT created a downloadable `example.py`.

### Inline code evidence

If a referenced code package is not physically present but the same assistant message contains fenced source code, the audit records that fact. The code may help reconstruct the work.

**Inline code is not considered equivalent to the original ZIP.** A ZIP may have contained multiple files, directory structure, binaries, diagrams, test data, or versions not recoverable from the displayed code alone.

## Status meanings

### `PHYSICALLY_PRESERVED`

A conversation artifact reference has one strong physical match inside the export ZIP.

This is the strongest preservation result.

### `PHYSICAL_MATCH_AMBIGUOUS`

More than one physical ZIP member could match the reference. The utility refuses to guess.

### `LIBRARY_REFERENCE_ONLY`

`library-files.json` appears to contain a record corresponding to the artifact, but no strong physical file match was found in the export.

This means the manifest evidence survived. It does **not** prove the file bytes survived.

### `NOT_PHYSICAL_INLINE_CODE_EVIDENCE`

No strong physical match was found, but the same message contains inline code evidence that may make partial reconstruction possible.

### `REFERENCE_ONLY_NOT_PHYSICAL`

The conversation contains an artifact reference, but this export contains no strong matching physical file and no stronger recovery evidence was found.

This does **not** prove permanent loss. The file could exist elsewhere: ChatGPT Library, a different export, your Downloads folder, GitHub, Google Drive, backups, or another local machine.

## Output files

The utility creates:

- `index.html` — searchable human report
- `summary.json` — aggregate counts
- `artifact_audit.csv` — one row per discovered artifact reference
- `artifact_audit.json` — detailed machine-readable evidence
- `unreferenced_physical_artifacts.csv` — artifact-like physical ZIP members that were not selected as conversation matches
- `README.txt` — privacy reminder

## The most important column: `reference_kind`

The report tells you **why** the utility believes an artifact existed:

- `sandbox_download` — very strong generated-download evidence
- `attachment_metadata` — strong conversation metadata evidence
- `file_service_pointer` — strong file-service identifier evidence
- `filename_mention` — weak textual evidence only

Do not treat these as equal.

## What to review first

For Intellectual Estate recovery, begin with assistant-generated `sandbox_download` rows whose status is:

1. `REFERENCE_ONLY_NOT_PHYSICAL`
2. `NOT_PHYSICAL_INLINE_CODE_EVIDENCE`
3. `LIBRARY_REFERENCE_ONLY`

Those are the artifacts most likely to deserve recovery attention.

A missing generated project ZIP may still be recoverable from:

- source code printed in the conversation;
- another generated version in a later conversation;
- ChatGPT Library;
- your local Downloads folders;
- GitHub repositories;
- Google Drive or other backups;
- source snapshots already preserved elsewhere in the Intellectual Estate.

## Command-line use

```bash
python audit_chatgpt_artifacts.py "chatgpt-export.zip" -o ChatGPT_Artifact_Audit
```

## What this tool intentionally does NOT claim

It does not claim that every filename mentioned in a conversation was a generated file.

It does not claim that a reference-only artifact is permanently lost.

It does not claim that inline code exactly recreates a missing multi-file package.

It does not modify, extract, or upload your original export.

Its job is to create an **evidence ledger** so you know where preservation is strong, weak, or uncertain.

## Design principle

```text
CONVERSATION SAYS IT EXISTED
            |
            v
    FIND STRONG REFERENCE
            |
            v
   MATCH PHYSICAL EXPORT
       /            \
      yes            no
      |              |
 PRESERVED      CHECK LIBRARY / CODE
                     |
                     v
             FLAG RECOVERY NEED
```

The purpose is not merely to preserve discussion about technical work. It is to determine whether the **finished work itself** survived.
