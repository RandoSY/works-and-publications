# ChatGPT Library Audit — Getting Started

**Purpose:** find out whether the files listed in a ChatGPT export's `library-files.json` can actually be matched to physical files inside that same export.

This is a companion to the ChatGPT Archive Browser. The two tools answer different questions:

| Tool | Input | Question answered |
|---|---|---|
| Conversation Browser | conversation JSON files | What conversations do I have, and how can I read/search them? |
| Library Audit | **original full ChatGPT export ZIP** | What Library records exist, which physical files are present, and which cannot be matched? |

## The single most important rule

**Run Library Audit on the ORIGINAL FULL ChatGPT export ZIP.**

Do **not** run it on `ChatGPT_Conversations_Only.zip` created by the conversation preparation tool. That smaller ZIP intentionally contains only conversation JSON and therefore does not contain the Library manifest or exported assets needed for an integrity comparison.

## What you need

Put these two files in the same folder:

- `audit_chatgpt_library.py`
- `audit_library_windows.bat`

You also need Python 3.9 or newer.

Check Python by opening Command Prompt and entering:

```text
python --version
```

## Easiest Windows procedure

1. Find the original ChatGPT export ZIP you downloaded from OpenAI.
2. Do **not** unzip it merely for this audit.
3. Drag that ZIP file onto `audit_library_windows.bat`.
4. A console window will show the source and output folder.
5. The audit reads the ZIP directory and `library-files.json` without extracting the whole archive.
6. When finished, it opens:

```text
ChatGPT_Library_Audit\index.html
```

Keep the original export unchanged as your source-of-truth backup.

## What the audit produces

The output folder contains:

- `index.html` — human-readable searchable report
- `summary.json` — overall counts and audit metadata
- `library_audit.csv` — one row per Library manifest record
- `library_audit.json` — the same detailed records in JSON form
- `unmatched_physical_files.csv` — physical export files not selected as Library matches
- `README.txt` — privacy reminder

## Understanding the three Library outcomes

### MATCHED

The utility found one physical export entry with strong evidence linking it to the Library record. Evidence can include:

- exact export path
- exact filename
- file/asset identifier
- filename stem equal to an identifier
- SHA-256, when present and `--hash` is used

### AMBIGUOUS

More than one physical file is equally plausible. A common example is the same filename appearing in two different folders.

Ambiguous does **not** mean missing. It means the audit refuses to guess.

### MISSING

No sufficiently strong physical match was found.

That can mean:

- the referenced file is genuinely absent from the export;
- the export schema changed and the utility does not yet recognize the linking field;
- the manifest does not expose enough information for deterministic matching.

For that reason, the report says **"could not be matched"**, not "OpenAI deleted this file."

## What "unmatched physical files" means

The audit also lists non-structural files that were not selected as Library matches.

These are **not automatically orphan files**. They may be:

- files attached to conversations;
- generated conversation assets;
- files belonging to another export feature;
- duplicated copies;
- items the Library manifest describes in a way the current matcher cannot yet resolve.

Treat the list as an investigation queue, not an error list.

## Why size alone is not enough

Two unrelated files can have exactly the same byte size. Therefore the utility deliberately refuses to call a record "matched" using size alone.

This conservative rule produces more `ambiguous` or `missing` results, but avoids false confidence.

## Optional SHA-256 verification

If `library-files.json` contains SHA-256 values, you can enable hashing:

```text
python audit_chatgpt_library.py "chatgpt-export.zip" --output ChatGPT_Library_Audit --hash --overwrite
```

Hash mode can be slower because file contents must be read. On a multi-gigabyte export, start without `--hash`; use it when hashes are actually needed to resolve uncertain records.

## If the report says "No library-files.json was found"

Check the input first.

The most common mistake is accidentally supplying `ChatGPT_Conversations_Only.zip` instead of the original full OpenAI export.

If you definitely used the original export and the manifest is still absent, preserve that export unchanged. Export formats can vary over time, and the absence of `library-files.json` is itself useful evidence about that export.

## Privacy

The generated report does not copy file contents into the HTML, but filenames, IDs, paths, MIME types, and origin metadata can still be sensitive.

**Keep the generated `ChatGPT_Library_Audit` folder private unless you intentionally sanitize it.**

The utility itself is local and read-only. It does not upload the export or report anywhere.

## How this fits the larger archive workflow

```text
                    ORIGINAL FULL CHATGPT EXPORT.ZIP
                           /                  \
                          /                    \
                         v                      v
        prepare conversation JSON       Library Audit
                 |                           |
                 v                           v
      ChatGPT_Conversations_Only.zip   integrity report
                 |
                 v
       Conversation Browser
                 |
                 v
       searchable history / catalog
```

The original export remains the evidence source. The conversation browser makes the text intelligible. The Library Audit tests whether the file-manifest side of the export is internally complete enough to reconstruct.

## Current evidence and limits

OpenAI currently documents that data exports can include conversation JSON plus files and other assets used in conversations. OpenAI also documents that uploaded and generated files are saved to Library where Library is available. A recent OpenAI Developer Community report described `library-files.json` records for which some physical files could not be found in the export. That community report is useful motivation for auditing, but it is not a specification of what every export must contain.

The utility therefore reports **observable export integrity** and avoids claiming what OpenAI was required to include.
