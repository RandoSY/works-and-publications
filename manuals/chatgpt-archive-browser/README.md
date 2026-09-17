# ChatGPT Archive Toolkit

Turn a very large ChatGPT data export into something you can **inspect, browse, audit, and understand** locally.

The toolkit now has four distinct jobs. They intentionally remain separate because they answer different questions.

| Layer | Tool | Question |
|---|---|---|
| 0 | **Export Spy** | What is physically inside this ZIP? |
| 1 | **Conversation Browser** | What conversations do I have, in what order, and what do they say? |
| 1 | **Library Audit** | Does `library-files.json` correspond to physical exported files? |
| 1 | **Artifact Preservation Audit** | Did the finished downloadable ZIPs/code/documents referenced in conversations physically survive? |

All tools are local and read-only with respect to the original export. They use the Python standard library only.

> **Privacy:** generated reports can expose conversation titles, filenames, IDs, paths, and other private information. Keep them private unless intentionally sanitized.

## Recommended order

```text
ORIGINAL FULL CHATGPT EXPORT.zip
            |
            v
      0. EXPORT SPY
      "What is here?"
            |
       +----+----------------------+
       |                           |
       v                           v
Conversation corpus           Full asset side
       |                           |
       v                           +-------------------+
Conversation Browser                              |
                                                   v
                                      Library Audit + Artifact Audit
                                                   |
                      +----------------------------+
                      v
               evidence + chronology
                      |
                      v
                 AI synthesis
                      |
                      v
                Project Atlas
```

## 0 — Export Spy

Files:

- `chatgpt_export_spy.py`
- `spy_windows.bat`
- `EXPORT_SPY_GUIDE.md`

Drag the original export ZIP onto `spy_windows.bat` to get a fast structural census from ZIP metadata without parsing all conversations.

Use this first when you simply want to know what classes of material are physically present.

## 1A — Conversation Browser

Printable guide: `ChatGPT_Archive_Browser_User_Guide_v1.1.0.pdf`

Files:

- `prepare_conversations_zip.py`
- `prepare_windows.bat`
- `chatgpt_archive_browser.py`
- `run_windows.bat`

The recommended novice workflow is:

```text
ORIGINAL FULL EXPORT.zip
        |
        | prepare_windows.bat
        v
ChatGPT_Conversations_Only.zip
        |
        | run_windows.bat
        v
ChatGPT_Archive_Browser/index.html
```

The browser sorts by actual conversation timestamps rather than numbered JSON filenames and provides local search, chronology, filters, counts, and one readable transcript page per conversation.

## 1B — Library Audit

Guide: `LIBRARY_AUDIT_GUIDE.md`

Files:

- `audit_chatgpt_library.py`
- `audit_library_windows.bat`

Run this against the **original full export ZIP**, not the reduced conversation-only ZIP.

It compares `library-files.json` with physical ZIP members and reports matched, ambiguous, and missing manifest records plus unmatched physical files.

## 1C — Artifact Preservation Audit

Guide: `ARTIFACT_PRESERVATION_GUIDE.md`

Files:

- `audit_chatgpt_artifacts.py`
- `audit_artifacts_windows.bat`

This answers a different and especially important question for technical work:

> A conversation says ChatGPT produced `MyProject.zip`, `main.py`, `firmware.ino`, a KiCad project, a PDF, or another downloadable result. **Did the artifact itself survive, or only the conversation that described it?**

The audit looks for strong download evidence such as `sandbox:/mnt/data/...`, attachment metadata, file-service IDs, Library evidence, physical ZIP members, and inline code that may aid reconstruction.

Statuses include:

- `PHYSICALLY_PRESERVED`
- `PHYSICAL_MATCH_AMBIGUOUS`
- `LIBRARY_REFERENCE_ONLY`
- `NOT_PHYSICAL_INLINE_CODE_EVIDENCE`
- `REFERENCE_ONLY_NOT_PHYSICAL`

A reference-only result is not proof of permanent loss. It means no strong physical match was found **in the supplied export**.

## Why four tools instead of one giant program?

Because there are four different levels of certainty:

1. **ZIP census** — physical member names and sizes are objective and fast.
2. **Conversation reconstruction** — chronology and text answer what was discussed.
3. **Manifest / artifact reconciliation** — evidence must be matched conservatively.
4. **Interpretation** — AI and human judgment determine what the corpus means.

Combining all of those into one opaque score would make the archive harder to trust.

## Command-line summary

Export census:

```bash
python chatgpt_export_spy.py "chatgpt-export.zip" -o ChatGPT_Export_Spy
```

Prepare conversation corpus:

```bash
python prepare_conversations_zip.py "chatgpt-export.zip" -o ChatGPT_Conversations_Only.zip
```

Build conversation browser:

```bash
python chatgpt_archive_browser.py "ChatGPT_Conversations_Only.zip" -o ChatGPT_Archive_Browser
```

Audit Library manifest:

```bash
python audit_chatgpt_library.py "chatgpt-export.zip" -o ChatGPT_Library_Audit
```

Audit generated/downloadable artifacts:

```bash
python audit_chatgpt_artifacts.py "chatgpt-export.zip" -o ChatGPT_Artifact_Audit
```

## Preservation model

```text
PRESERVE ORIGINAL EXPORT
          |
          v
        CENSUS
          |
    +-----+-----+
    |           |
    v           v
CONVERSATIONS  ASSETS
    |           |
    v           v
  BROWSE   AUDIT LIBRARY + ARTIFACTS
    \           /
     \         /
      v       v
      EVIDENCE LEDGER
            |
            v
      AI + HUMAN SYNTHESIS
```

The original export remains the source evidence. None of these tools replaces it.

## License

MIT. See `LICENSE`.
