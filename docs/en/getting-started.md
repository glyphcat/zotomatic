# Getting Started

## 1. Install

```bash
pip install zotomatic
```

## 2. Initialize (first run only)

Create the config file and template.

```bash
zotomatic init --pdf-dir "~/Zotero/storage"
```

`--pdf-dir` is required. On subsequent runs, `init` does not overwrite existing values; it only fills in missing settings or templates.

Default config paths:

- macOS/Linux: `~/.zotomatic/config.toml`
- Windows: `%LOCALAPPDATA%\\Zotomatic\\config.toml`

## 3. Review and edit the config

At minimum, set `pdf_dir`. Adjust other settings as needed.

- `pdf_dir`: root directory to scan (required)
- `note_dir`: output directory for notes (default used if unset)
- `note_title_pattern` / `template_path`: note name and template (defaults used if unset)
- `zotero_api_key` / `zotero_library_id`: required to use Zotero integration
- `llm_openai_api_key`: required for LLM summaries and tags

If you want Zotero metadata, keep the Zotero desktop app running. Notes can still be generated for PDFs outside Zotero or when Zotero is not running, but metadata will be minimal.

Example:

```toml
pdf_dir = "~/Zotero/storage"
note_dir = "~/Documents/Notes/Zotomatic"
note_title_pattern = "{{ year }}-{{ slug80 }}-{{ citekey }}"
template_path = "~/Zotomatic/templates/note.md"
```

Update settings via `config.toml` or environment variables. See `configuration.md` for the env var list.

## 4. Pre-flight check (recommended)

```bash
zotomatic doctor
```

This checks whether the standard workflow (`scan --once` or `scan --watch`) can run. If you only use `scan --path`, `pdf_dir` does not need to be configured.

## 5. Generate notes (scan)

`scan` has three modes. Modes cannot be combined.

### `--once` (default)

Scan `pdf_dir` once and exit.

```bash
zotomatic scan --once
```

### `--watch`

Scan once at startup, then watch for new PDFs. Stop with `Ctrl+C`.

```bash
zotomatic scan --watch
```

### `--path <pdf...>`

Process the specified PDFs in order and exit. `pdf_dir` is not required.

```bash
zotomatic scan --path ~/Downloads/a.pdf ~/Downloads/b.pdf
```

### `--force` (re-scan)

With `--once` / `--watch`, include PDFs that were skipped in previous runs. Existing notes may still be skipped or updated as usual. If a note has pending summary/tag status, it may be updated.

```bash
zotomatic scan --once --force
```

## 6. LLM summaries and tags (optional)

When `llm_openai_api_key` is set, Zotomatic can auto-insert summaries and tags into notes. If unset, notes are generated without LLM output.
