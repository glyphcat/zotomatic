# CLI Reference

## Command List

- `scan`: process PDFs and generate notes
- `init`: prepare config, templates, and DB
- `config`: show or reset settings
- `template`: create or switch note templates
- `doctor`: check configuration and integrations

## scan

### What it does

Process PDFs and generate notes.

### Usage

```bash
zotomatic scan [--once | --watch] [--force]
zotomatic scan --path <pdf...>
```

- `--once` / `--watch` require `pdf_dir` to be configured.
- `--path` does not require `pdf_dir`.

### Modes (mutually exclusive)

- `--once` (default)
  - Scan `pdf_dir` once and exit.
  - Example: `zotomatic scan --once`
- `--watch`
  - Scan once at startup, then watch for new PDFs and keep running.
  - Stop with `Ctrl+C`.
  - Example: `zotomatic scan --watch`
- `--path <pdf...>`
  - Process the specified PDFs in order and exit.
  - Example: `zotomatic scan --path ~/Downloads/a.pdf ~/Downloads/b.pdf`

### Additional options

- `--force`
  - Include PDFs that were skipped in previous runs.
  - Cannot be used with `--path`.
  - Example: `zotomatic scan --watch --force`

## init

### What it does

Initialize the config and template, and prepare the DB. On subsequent runs, it does not overwrite existing values and only fills missing settings or templates.

### Usage

```bash
zotomatic init --pdf-dir <path> [--note-dir <path>] [--template-path <path>] [--llm-provider <openai|gemini>]
```

### What gets created

- Config file:
  - macOS/Linux: `~/.zotomatic/config.toml`
  - Windows: `%LOCALAPPDATA%\\Zotomatic\\config.toml`
- Template:
  - Default: `~/Zotomatic/templates/note.md`
  - When `--template-path` is provided, that path is used
- SQLite DB:
  - macOS/Linux: `~/.zotomatic/db/zotomatic.db`
  - Windows: `%LOCALAPPDATA%\\Zotomatic\\db\\zotomatic.db`

### Options

- `--pdf-dir` (required)
  - Root directory containing PDFs to scan.
  - Example: `zotomatic init --pdf-dir ~/Zotero/storage`
- `--note-dir`
  - Output directory for notes (default: `~/Zotomatic/notes`).
  - Example: `zotomatic init --pdf-dir ~/Zotero/storage --note-dir ~/Documents/Obsidian/Zotomatic`
- `--template-path`
  - File path for the note template.
  - Example: `zotomatic init --pdf-dir ~/Zotero/storage --template-path ~/Zotomatic/templates/note.md`
- `--llm-provider`
  - LLM provider (`openai`, `gemini`).
  - `chatgpt` is an alias for `openai`.
  - Example: `zotomatic init --pdf-dir ~/Zotero/storage --llm-provider openai`

## config

### What it does

Show the effective configuration, reset to defaults, or migrate schema versions.

### Usage

```bash
zotomatic config
zotomatic config show
zotomatic config default
zotomatic config migrate
```

### Subcommands

- `show`
  - Show the effective configuration values.
  - Example: `zotomatic config show`
- `default`
  - Reset to defaults and create `config.toml.bak`.
  - Example: `zotomatic config default`
- `migrate`
  - Migrate config values to the latest schema.
  - Example: `zotomatic config migrate`

## template

### What it does

Create or switch note templates.

### Usage

```bash
zotomatic template create --path <path>
zotomatic template set --path <path>
```

### Subcommands

- `create --path <path>`
  - Create a template file and update `template_path`.
  - Example: `zotomatic template create --path ~/Zotomatic/templates/note.md`
- `set --path <path>`
  - Set `template_path` to an existing template.
  - Example: `zotomatic template set --path ~/Zotomatic/templates/note.md`

## doctor

### What it does

Check configuration, paths, and integration health.

### Usage

```bash
zotomatic doctor
```

## llm

### What it does

Update LLM settings.

### Usage

```bash
zotomatic llm set --provider <openai|gemini> [--api-key <key>] [--model <name>] [--base-url <url>]
```

### Subcommands

- `set`
  - Update LLM settings.
  - `--provider` is required.
  - `--api-key` is optional; if omitted, environment variables are used.

### Options

- `--provider` (required)
  - LLM provider (`openai`, `gemini`).
  - `chatgpt` is an alias for `openai`.
- `--api-key`
  - API key. If omitted, `ZOTOMATIC_LLM_<PROVIDER>_API_KEY` is used.
- `--model`
  - LLM model name.
- `--base-url`
  - LLM base URL.
