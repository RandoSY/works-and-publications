# ChatGPT Archive Browser

Turn a very large ChatGPT data export into a private, searchable, chronological website that runs entirely on your own computer.

This project is for the point where a ChatGPT export is no longer a convenient backup but a corpus: years of conversations, many numbered JSON files, gigabytes of attachments, and no practical way to review the history in order.

## What problem does this solve?

OpenAI data exports can contain `conversations.json`; larger exports may contain numbered conversation JSON files instead. OpenAI also notes that importing those files into another ChatGPT account makes them available as reference, but does **not** recreate the original conversations in the sidebar. See OpenAI's current help article: https://help.openai.com/en/articles/9106926

For a large archive, three things become awkward:

1. The export is designed as data, not as a human-scale reading interface.
2. The numbered files are chunks of the export, **not a trustworthy chronological table of contents**.
3. A multi-gigabyte archive is too large to treat as one document or one browser page.

The solution used here is deliberately simple: transform the conversation records into a static local website.

## What it builds

The generator produces:

- `index.html` — searchable master index
- `conversations/` — one readable HTML transcript per conversation
- `catalog.json` — machine-readable chronological catalog
- `README.txt` — a reminder that the generated material is private

The index supports:

- true oldest-to-newest chronology using each conversation's `create_time`
- newest-first, title, and length sorting
- year and month filtering
- broad heuristic topic categories
- model information when present in the export
- title and indexed user-text search
- opening-prompt previews
- message and word counts
- Previous / Next navigation through the whole archive

Everything is static HTML. No database server, web server, cloud account, or JavaScript framework is required.

## Why this scales better than one giant HTML file

A multi-gigabyte export should not become a multi-gigabyte web page.

This tool instead:

- reads the ZIP directly; it does not extract the entire export first
- scans only `conversations.json` / `conversations-###.json`
- parses top-level JSON arrays incrementally
- writes each conversation to its own HTML file
- keeps only a compact catalog/search summary in memory
- caps indexed user text per conversation (6,000 characters by default)
- leaves large exported images and attachments untouched

The result is much easier for an ordinary browser to handle.

## Requirements

- Python 3.9 or newer
- A modern browser
- Enough free disk space for the generated HTML transcripts

No third-party Python packages are required.

## Fastest use on Windows

1. Download this repository or at least `chatgpt_archive_browser.py` and `run_windows.bat`.
2. Put both files in the same folder.
3. Drag your ChatGPT export ZIP onto `run_windows.bat`.
4. The script creates `ChatGPT_Archive_Browser` next to the ZIP.
5. When finished, it opens `index.html`.

## Command-line use

```bash
python chatgpt_archive_browser.py "chatgpt-export.zip" -o ChatGPT_Archive_Browser
```

Then open `ChatGPT_Archive_Browser/index.html`.

You can also point it at an already-extracted export directory:

```bash
python chatgpt_archive_browser.py "/path/to/export-folder" -o ChatGPT_Archive_Browser
```

Or a single conversation JSON file:

```bash
python chatgpt_archive_browser.py conversations.json -o ChatGPT_Archive_Browser
```

### Useful options

Test on the first 100 conversations:

```bash
python chatgpt_archive_browser.py export.zip -o browser-test --limit 100
```

Replace an existing output folder:

```bash
python chatgpt_archive_browser.py export.zip -o ChatGPT_Archive_Browser --overwrite
```

Change how much user text is placed in the fast local search index:

```bash
python chatgpt_archive_browser.py export.zip -o ChatGPT_Archive_Browser --index-chars 12000
```

The full transcripts are still written even when the fast search index is capped.

## Recommended workflow for very large exports (>7 GB)

### 1. Preserve the original ZIP

Treat the downloaded ChatGPT export as the source-of-truth backup. Do not modify it. Work from a copy if possible.

### 2. Put the export on a drive with room to spare

The generator does not extract all assets, but the HTML transcript set can still become large. Leave several gigabytes of free space.

### 3. Run a small test first

```bash
python chatgpt_archive_browser.py export.zip -o browser-test --limit 100
```

Open `browser-test/index.html` and verify that titles, dates, and transcripts look sensible.

### 4. Build the complete browser

```bash
python chatgpt_archive_browser.py export.zip -o ChatGPT_Archive_Browser --overwrite
```

Large archives take time because every conversation record must be parsed and rendered. The script prints progress as it works.

### 5. Start with chronology, not filenames

The archive index sorts on the actual `create_time` recorded inside each conversation. Do not assume that `conversations-000.json`, `conversations-001.json`, and so forth represent oldest-to-newest history.

### 6. Use the browser as the human interface and `catalog.json` as the machine interface

`index.html` is for reading and finding things.

`catalog.json` is useful for later analysis: topic inventories, timelines, project extraction, statistics, or feeding selected subsets into other tools.

## Privacy and security

A ChatGPT data export can contain extremely personal material. The generated website contains readable copies of conversation text.

**Do not publish your generated archive directory to GitHub or a public web host unless you have intentionally reviewed and sanitized it.**

The generator itself sends nothing anywhere. It uses only local Python file I/O. The HTML browser works locally with `file://` URLs and does not require a network connection.

Conversation text is HTML-escaped before being written to pages. That prevents archived HTML or script fragments from being executed as page markup.

## What is intentionally not copied

The tool concentrates on the conversation corpus. It does not duplicate the export's potentially enormous attachment/media tree into the generated browser.

Non-text message content may appear as a placeholder. The original export remains the authoritative source for files, images, and other assets.

## Topic labels are only navigation aids

Topic classification is a lightweight keyword heuristic. It is useful for coarse browsing, but it is not an AI judgment about the meaning of a conversation. Expect an `Other` category and occasional imperfect labels.

If you need rigorous thematic analysis, use `catalog.json` as the starting point for a separate analysis pass.

## Export schema changes

ChatGPT's export format can evolve. This program is intentionally defensive about missing fields and message branches, but future changes may require updates.

If a newer export stops working, keep the original ZIP intact and report the smallest reproducible structural example that does **not** contain private conversation text.

## Design principle

```text
opaque multi-gigabyte export
        ↓
streaming parse of conversation JSON
        ↓
chronological catalog + one page per conversation
        ↓
private local website you can actually read
```

The goal is not to replace the original export. It is to make the export intelligible.

## License

MIT. See `LICENSE`.
