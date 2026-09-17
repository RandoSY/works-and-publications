# ChatGPT Archive Toolkit

Turn a very large ChatGPT data export into something you can **understand, browse, and audit** on your own computer.

This toolkit has two independent but complementary jobs:

1. **Conversation Browser** — reconstruct the conversation corpus into a searchable chronological local website.
2. **Library Audit** — compare `library-files.json` with the physical files actually present in the original export.

No cloud service or third-party Python package is required. The tools are read-only with respect to the original export.

> **Privacy first:** a ChatGPT export can contain highly personal material. Keep the original export, working ZIPs, generated browser, and audit reports private unless you deliberately sanitize them.

## Which tool do I use?

| If you want to know... | Use | Input |
|---|---|---|
| What conversations do I have? | Conversation Browser | conversation JSON corpus |
| What did I say first? How did ideas evolve? | Conversation Browser | conversation JSON corpus |
| Which Library files are physically present in my export? | Library Audit | **original full export ZIP** |
| Which Library records cannot be matched to a physical file? | Library Audit | **original full export ZIP** |

### Important input distinction

The Conversation Browser deliberately works from a reduced `ChatGPT_Conversations_Only.zip`.

The Library Audit must work from the **ORIGINAL FULL ChatGPT export ZIP**, because it needs both the Library manifest and the physical exported assets.

Do not audit the conversation-only ZIP.

---

# Part A — Conversation Browser

**Printable guide:** [ChatGPT Archive Browser — Getting Started User Guide v1.1.0 (PDF)](ChatGPT_Archive_Browser_User_Guide_v1.1.0.pdf)

## Why prepare a conversation-only ZIP?

A large ChatGPT export can contain gigabytes of images, files, metadata, and one or many conversation JSON files. For conversation analysis, repeatedly processing all those assets is unnecessary.

```text
ORIGINAL CHATGPT EXPORT.zip
        (source of truth)
                |
                | Stage 1 — collect conversation JSON only
                v
ChatGPT_Conversations_Only.zip
        (small working corpus)
                |
                | Stage 2 — build readable local website
                v
ChatGPT_Archive_Browser/
    index.html
    conversations/
    catalog.json
```

## What to download for the Conversation Browser

Put these four files together in one folder such as `C:\ChatGPT-Archive-Tools`:

- `prepare_conversations_zip.py`
- `prepare_windows.bat`
- `chatgpt_archive_browser.py`
- `run_windows.bat`

You need Python 3.9 or newer.

## Stage 1 — make a clean conversation-only ZIP

1. Keep the original ChatGPT export ZIP unchanged.
2. Drag the original export ZIP onto `prepare_windows.bat`.
3. The helper finds `conversations.json` or all numbered `conversations-###.json` files.
4. It creates `ChatGPT_Conversations_Only.zip` beside the original export.
5. It adds `CONVERSATION_FILES_MANIFEST.txt` listing exactly what was collected.
6. It verifies the new ZIP before reporting success.

The new ZIP should be much smaller than the original because it intentionally excludes attachment/media assets.

## Stage 2 — build the browser

1. Drag `ChatGPT_Conversations_Only.zip` onto `run_windows.bat`.
2. The generator creates `ChatGPT_Archive_Browser` beside the ZIP.
3. When finished, `index.html` opens automatically.

The browser provides chronology, search, year/topic filtering, model information, opening-prompt previews, message/word counts, and Previous/Next navigation.

**Numbered conversation filenames are export chunks, not a chronological table of contents.** The browser sorts by each conversation's recorded `create_time`.

---

# Part B — Library Audit

**Getting started:** [Library Audit Guide](LIBRARY_AUDIT_GUIDE.md)

## What problem does this solve?

`library-files.json` is a manifest/catalog. The audit asks a different question:

> For every Library record in the manifest, can I find a physical file inside the same export that strongly matches it?

The audit does not modify or extract the full archive. It reads ZIP metadata directly and reports observable consistency.

## What to download for Library Audit

Put these two files beside the other toolkit files:

- `audit_chatgpt_library.py`
- `audit_library_windows.bat`

## Easiest Windows procedure

1. Find your **original full ChatGPT export ZIP**.
2. Do not use `ChatGPT_Conversations_Only.zip`.
3. Drag the original full export onto `audit_library_windows.bat`.
4. The tool creates `ChatGPT_Library_Audit` beside the export.
5. When finished it opens `ChatGPT_Library_Audit\index.html`.

## What the Library Audit creates

- `index.html` — searchable human report
- `summary.json` — overall counts
- `library_audit.csv` — one row per Library record
- `library_audit.json` — detailed machine-readable audit
- `unmatched_physical_files.csv` — non-structural physical files not selected as Library matches
- `README.txt` — privacy reminder

## Interpreting the results

**MATCHED** — one physical export entry has strong evidence linking it to the Library record, such as path, filename, file/asset ID, or optional SHA-256.

**AMBIGUOUS** — more than one physical file is equally plausible. The utility refuses to guess.

**MISSING** — no sufficiently strong physical match was found. That may indicate an absent asset, changed export schema, or insufficient manifest metadata. It does **not**, by itself, prove deletion or an OpenAI defect.

**UNMATCHED PHYSICAL FILES** — physical export files not selected as Library matches. These may belong to conversations or other export features and are not automatically errors.

Size alone never counts as a match.

## Optional SHA-256 verification

If the manifest exposes SHA-256 values:

```bash
python audit_chatgpt_library.py "chatgpt-export.zip" -o ChatGPT_Library_Audit --hash --overwrite
```

Hash mode is intentionally optional because reading every candidate file can be slower on very large exports.

---

# Command-line equivalents

Prepare conversation corpus:

```bash
python prepare_conversations_zip.py "chatgpt-export.zip" -o ChatGPT_Conversations_Only.zip
```

Build browser:

```bash
python chatgpt_archive_browser.py "ChatGPT_Conversations_Only.zip" -o ChatGPT_Archive_Browser
```

Audit Library integrity:

```bash
python audit_chatgpt_library.py "chatgpt-export.zip" -o ChatGPT_Library_Audit --overwrite
```

---

# The complete archive workflow

```text
                         ORIGINAL FULL CHATGPT EXPORT.zip
                              /                    \
                             /                      \
                            v                        v
               collect conversation JSON       Library Audit
                         |                        manifest ↔ files
                         v                            |
              ChatGPT_Conversations_Only.zip          v
                         |                    integrity evidence
                         v
               Conversation Browser
                         |
                         v
           searchable chronology + catalog
                         |
                         v
                  AI / human synthesis
```

The original export remains the evidence source. The browser makes conversation history intelligible. The Library Audit checks the asset-manifest side of the export. Neither replaces the original export.

# Why these tools exist

Once a ChatGPT history grows to thousands of conversations and gigabytes of assets, manual inspection stops being practical. A useful archive needs separate layers:

- **preservation** — keep the original export unchanged;
- **retrieval** — make conversations searchable and chronological;
- **integrity** — determine what asset records can actually be matched to physical files;
- **analysis** — use the catalog and reports to understand the corpus;
- **human judgment** — decide what matters and what should survive.

# Privacy and security

The tools use local Python file I/O and do not upload your archive.

The generated browser contains conversation text. The Library Audit report can contain sensitive filenames, paths, IDs, and metadata even though it does not embed file contents.

**Do not publish generated output folders unless you have intentionally reviewed and sanitized them.**

# Current OpenAI context

OpenAI's current documentation states that a data export can include conversation JSON plus files and other assets used in conversations. OpenAI also documents Library as the place where uploaded and generated files are saved when Library is available.

A recent OpenAI Developer Community report described Library manifest records whose corresponding physical files could not be found in an export. That report motivates integrity checking, but it is not treated here as a formal export specification. The Library Audit therefore reports only what is observable in the supplied export.

Official references:

- https://help.openai.com/en/articles/9106926
- https://help.openai.com/en/articles/20001052

# Design principles

Conversation workflow:

```text
PRESERVE -> COLLECT -> VERIFY -> BUILD -> BROWSE
```

Library workflow:

```text
PRESERVE -> INVENTORY -> MATCH -> FLAG UNCERTAINTY -> REVIEW
```

# License

MIT. See `LICENSE`.
