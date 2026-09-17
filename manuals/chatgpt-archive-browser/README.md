# ChatGPT Archive Browser

Turn a very large ChatGPT data export into a private, searchable, chronological website that runs entirely on your own computer.

**Start here if you are not technical:** use the two-stage Windows workflow below. It deliberately separates **preparing the conversation files** from **building the browser**, so you can see and verify what is happening.

**Printable guide:** [ChatGPT Archive Browser - Getting Started User Guide v1.1.0 (PDF)](ChatGPT_Archive_Browser_User_Guide_v1.1.0.pdf)

> **Privacy first:** your ChatGPT export can contain highly personal material. Keep the original export, the conversation-only working ZIP, and the generated browser private unless you deliberately sanitize them.

## The problem

A large ChatGPT export is an excellent backup, but a poor reading interface. It may contain gigabytes of images, files, metadata, and one or many conversation JSON files. OpenAI documents that larger exports may contain numbered conversation JSON files rather than one `conversations.json` file.

The browser solves a different problem: **make the conversation history intelligible to a human**.

```text
ORIGINAL CHATGPT EXPORT.zip
        (source of truth)
                |
                | Stage 1 - collect conversation JSON only
                v
ChatGPT_Conversations_Only.zip
        (small working corpus)
                |
                | Stage 2 - build readable local website
                v
ChatGPT_Archive_Browser/
    index.html
    conversations/
    catalog.json
```

## What to download

Put these four files together in one folder such as `C:\ChatGPT-Archive-Tools`:

- `prepare_conversations_zip.py`
- `prepare_windows.bat`
- `chatgpt_archive_browser.py`
- `run_windows.bat`

You also need Python 3.9 or newer. No third-party Python packages are required.

## Stage 1 - make a clean conversation-only ZIP

### Recommended Windows method

1. **Keep the original ChatGPT export ZIP unchanged.** Treat it as your master backup.
2. Drag the original export ZIP onto `prepare_windows.bat`.
3. The helper scans the ZIP without extracting the entire multi-gigabyte export.
4. It finds only:
   - `conversations.json`, or
   - numbered files such as `conversations-000.json`, `conversations-001.json`, ...
5. It creates `ChatGPT_Conversations_Only.zip` beside the original export.
6. It adds `CONVERSATION_FILES_MANIFEST.txt` so you can see exactly which conversation JSON files were collected.
7. It verifies the new ZIP before reporting success.

The new ZIP is **supposed to be much smaller** than the original export. It does not copy the large attachment and media tree.

### What success looks like

For a large export, opening `ChatGPT_Conversations_Only.zip` should show something like:

```text
conversations-000.json
conversations-001.json
conversations-002.json
...
CONVERSATION_FILES_MANIFEST.txt
```

For a smaller export, you may see only:

```text
conversations.json
CONVERSATION_FILES_MANIFEST.txt
```

If the helper detects gaps in a numbered sequence, it warns you. Do not casually ignore that warning; first confirm the original export is complete.

### Manual fallback: collect the JSON files yourself

If you prefer not to use the helper:

1. Right-click the original export ZIP and choose **Extract All**.
2. Open the extracted folder.
3. Search for `conversations*.json`.
4. Copy **every** conversation JSON result into a new empty folder called `ChatGPT_Conversation_JSON`.
5. If the files are numbered, sort by name and check that the sequence appears complete (`000`, `001`, `002`, ...).
6. Do **not** substitute unrelated JSON files such as feedback, account, or shared-link metadata.
7. Select the collected conversation JSON files and choose **Compress to ZIP file** (Windows 11) or **Send to > Compressed (zipped) folder** on older Windows versions.
8. Name the result `ChatGPT_Conversations_Only.zip`.

The automated helper is safer because it searches the original ZIP directly, avoids accidentally collecting unrelated JSON files, checks the numbered sequence, and verifies the output ZIP.

## Stage 2 - build the browser

1. Drag `ChatGPT_Conversations_Only.zip` onto `run_windows.bat`.
2. The browser generator reads the conversation records and creates a folder named `ChatGPT_Archive_Browser` beside the ZIP.
3. When the build finishes, `index.html` opens automatically.

Inside the generated folder:

- `index.html` - searchable master index
- `conversations/` - one readable HTML transcript per conversation
- `catalog.json` - machine-readable chronological catalog
- `README.txt` - privacy reminder

## Why this two-stage setup is useful

The original export is a backup of many kinds of account data. The conversation-only ZIP is a **working corpus**. Keeping those roles separate has several advantages:

- you never modify the master export;
- you can confirm exactly which conversation files are being analyzed;
- you avoid repeatedly processing gigabytes of attachments and media;
- the smaller working ZIP is easier to copy, archive, or feed into other local tools;
- troubleshooting becomes much simpler because the browser input contains only conversation records.

## What the browser gives you

The local index supports:

- true oldest-to-newest chronology using each conversation's `create_time`
- newest-first, title, and length sorting
- year filtering
- broad heuristic topic categories
- model information when present
- title and indexed user-text search
- opening-prompt previews
- message and word counts
- Previous / Next navigation through the full archive

**Important:** numbered filenames are export chunks, not a chronological table of contents. The browser sorts by the timestamps inside the conversations.

## Command-line equivalents

Prepare the working ZIP:

```bash
python prepare_conversations_zip.py "chatgpt-export.zip" -o ChatGPT_Conversations_Only.zip
```

Build the browser:

```bash
python chatgpt_archive_browser.py "ChatGPT_Conversations_Only.zip" -o ChatGPT_Archive_Browser
```

Optional small test build:

```bash
python chatgpt_archive_browser.py "ChatGPT_Conversations_Only.zip" -o browser-test --limit 100
```

## Why this scales to multi-gigabyte exports

The browser does not try to turn the full export into one enormous HTML page. It:

- reads ZIP members directly;
- scans only conversation JSON;
- incrementally parses top-level JSON arrays;
- writes one HTML file per conversation;
- keeps a compact search catalog in memory;
- leaves large attachment/media assets in the original export.

## What is intentionally not copied

The generated browser concentrates on text conversation history. Large images, uploads, and other exported assets remain in the original export. Non-text content may appear as a placeholder.

The original export is therefore still the authoritative backup.

## Privacy and security

The tools use local Python file I/O. They do not upload your archive. The generated browser runs locally with `file://` URLs.

**Never publish the generated browser or `ChatGPT_Conversations_Only.zip` to a public repository unless you have intentionally reviewed and sanitized the contents.**

## Troubleshooting

### “Python 3 was not found”
Install Python 3 from https://www.python.org/downloads/. On Windows, select **Add python.exe to PATH** if offered. Close the command window and try again.

### “No conversations JSON files were found”
Make sure you supplied the original ChatGPT export ZIP, not a nested attachments ZIP or another archive.

### The working ZIP is dramatically smaller than the original
That is expected. It contains conversation JSON, not the export's images and file assets.

### The helper warns about missing numbered files
Stop and inspect the original export. A gap can mean an incomplete collection. Do not infer that the numbered filenames are dates; they are only export chunks.

### The browser contains no images from old conversations
Expected. This utility is a conversation-text browser, not a reconstruction of every exported asset.

## Official OpenAI reference

OpenAI's current help documentation states that an exported ZIP may contain `conversations.json`, while larger exports may contain numbered conversation JSON files instead. Uploading those files elsewhere does not recreate the original ChatGPT sidebar.

https://help.openai.com/en/articles/9106926

## Design principle

```text
PRESERVE -> COLLECT -> VERIFY -> BUILD -> BROWSE
```

Preserve the original. Collect the conversation corpus. Verify the working ZIP. Build a human interface. Then browse and analyze.

## License

MIT. See `LICENSE`.