# Configuration Reference

This document lists the settings that users can specify via the config file or environment variables.

## Config file location

- macOS/Linux: `~/.zotomatic/config.toml`
- Windows: `%LOCALAPPDATA%\\Zotomatic\\config.toml`

## Precedence

1. CLI options
2. Environment variables (prefixed with `ZOTOMATIC_`)
3. Config file
4. Package defaults

## Settings list

### Core settings

| config key | env var key | required | description |
| --- | --- | --- | --- |
| `note_dir` | `ZOTOMATIC_NOTE_DIR` | optional | Output directory for notes. |
| `notes_encoding` | `ZOTOMATIC_NOTES_ENCODING` | optional | Text encoding for notes. |
| `pdf_dir` | `ZOTOMATIC_PDF_DIR` | required | Root directory containing PDFs to scan. |
| `llm_output_language` | `ZOTOMATIC_LLM_OUTPUT_LANGUAGE` | optional | Output language code for LLM. Valid codes: `en`, `ja`, `zh`, `ko`, `es`, `pt`, `fr`, `de`, `it`, `nl`, `sv`, `pl`, `tr`, `ru`. |
| `llm_summary_mode` | `ZOTOMATIC_LLM_SUMMARY_MODE` | optional | Summary mode: `quick`, `standard`, `deep`. |
| `llm_tag_limit` | `ZOTOMATIC_LLM_TAG_LIMIT` | optional | Maximum number of tags to generate. |
| `llm_tag_enabled` | `ZOTOMATIC_LLM_TAG_ENABLED` | optional | Enable LLM tag generation. |
| `llm_summary_enabled` | `ZOTOMATIC_LLM_SUMMARY_ENABLED` | optional | Enable LLM summaries. |
| `llm_timeout` | `ZOTOMATIC_LLM_TIMEOUT` | optional | LLM API timeout in seconds (TOML float). |
| `llm_daily_limit` | `ZOTOMATIC_LLM_DAILY_LIMIT` | optional | Daily limit for LLM calls. |
| `zotero_api_key` | `ZOTOMATIC_ZOTERO_API_KEY` | conditional | Required for Zotero integration. |
| `zotero_library_id` | `ZOTOMATIC_ZOTERO_LIBRARY_ID` | optional | Zotero library ID (empty means user library). |
| `zotero_library_scope` | `ZOTOMATIC_ZOTERO_LIBRARY_SCOPE` | optional | Zotero scope: `user` / `group`. |
| `note_title_pattern` | `ZOTOMATIC_NOTE_TITLE_PATTERN` | optional | Filename template for notes. |
| `template_path` | `ZOTOMATIC_TEMPLATE_PATH` | optional | File path to the note template. |

### LLM settings

LLM settings live under `[llm]` and `[llm.providers.<provider>]`. `llm.provider` is required.
Documentation uses ChatGPT naming, but config uses `openai`.

| config key | env var key | required | description |
| --- | --- | --- | --- |
| `llm.provider` | `ZOTOMATIC_LLM_PROVIDER` | conditional | LLM provider (`openai` / `gemini`). |
| `llm.providers.openai.api_key` | `ZOTOMATIC_LLM_OPENAI_API_KEY` | conditional | Required for ChatGPT (OpenAI). |
| `llm.providers.openai.model` | `ZOTOMATIC_LLM_OPENAI_MODEL` | optional | ChatGPT model name. |
| `llm.providers.openai.base_url` | `ZOTOMATIC_LLM_OPENAI_BASE_URL` | optional | ChatGPT base URL. |
| `llm.providers.gemini.api_key` | `ZOTOMATIC_LLM_GEMINI_API_KEY` | conditional | Required for Gemini. |
| `llm.providers.gemini.model` | `ZOTOMATIC_LLM_GEMINI_MODEL` | optional | Gemini model name. |
| `llm.providers.gemini.base_url` | `ZOTOMATIC_LLM_GEMINI_BASE_URL` | optional | Gemini base URL. |

Notes on required/optional:

- required: needed for the feature to work
- conditional: required only when using a specific feature
- optional: defaults are used if unset

### Default values

| key | default |
| --- | --- |
| `note_dir` | `~/Zotomatic/notes` |
| `notes_encoding` | `utf-8` |
| `llm_output_language` | `ja` |
| `llm_summary_mode` | `quick` |
| `llm_tag_limit` | `8` |
| `llm_tag_enabled` | `true` |
| `llm_summary_enabled` | `true` |
| `llm_timeout` | `30.0` |
| `llm_daily_limit` | `50` |
| `zotero_api_key` | `(empty)` |
| `zotero_library_id` | `(empty)` |
| `zotero_library_scope` | `user` |
| `note_title_pattern` | `{{ year }}-{{ slug80 }}-{{ citekey }}` |
| `template_path` | `~/Zotomatic/templates/note.md` |
| `llm.provider` | `(empty)` |
| `llm.providers.openai.model` | `gpt-4o-mini` |
| `llm.providers.openai.base_url` | `https://api.openai.com/v1` |
| `llm.providers.gemini.model` | `gemini-2.0-flash` |
| `llm.providers.gemini.base_url` | `https://generativelanguage.googleapis.com/v1beta` |

### Config file example (config.toml)

```toml
pdf_dir = "~/Zotero/storage"
note_dir = "~/Documents/Obsidian/Zotomatic"
note_title_pattern = "{{ year }}-{{ slug80 }}-{{ citekey }}"
template_path = "~/Zotomatic/templates/note.md"

[llm]
provider = "openai"

[llm.providers.openai]
api_key = "sk-..."
```

### Environment variables

Only the environment variable keys listed above are effective. The prefix is removed and lowercased to map to config keys.
Set `ZOTOMATIC_LLM_PROVIDER` and the provider-specific keys (for example, `ZOTOMATIC_LLM_OPENAI_API_KEY`) together.

Example:

```bash
export ZOTOMATIC_LLM_PROVIDER=openai
export ZOTOMATIC_LLM_OPENAI_API_KEY=...
```

Note: `notes_encoding` and `llm_timeout` are best set in `config.toml`.

## `notes_encoding` (output encoding)

`notes_encoding` is available but intended for advanced users. `utf-8` is recommended.

## `llm_output_language` (LLM output language)

`llm_output_language` only injects the language into the prompt. Output quality and accuracy are not guaranteed.

### Language code table

| code | language |
| --- | --- |
| `de` | German |
| `en` | English |
| `es` | Spanish |
| `fr` | French |
| `it` | Italian |
| `ja` | Japanese |
| `ko` | Korean |
| `nl` | Dutch |
| `pl` | Polish |
| `pt` | Portuguese |
| `ru` | Russian |
| `sv` | Swedish |
| `tr` | Turkish |
| `zh` | Chinese |

## `llm_summary_mode` (summary mode)

`llm_summary_mode` controls how summaries are generated.

- `quick`: short summary based mainly on the abstract.
- `standard`: summary using the abstract and section snippets.
- `deep`: detailed summary produced by chunking and merging.

You can override the mode per run with `zotomatic scan --summary-mode <mode>`. This does not update your config file.

## `note_title_pattern` (note filename template)

`note_title_pattern` uses `{{ key }}` placeholders to build note filenames. Missing values become empty strings. If no extension is specified, `.md` is appended and filenames are sanitized.

### Available placeholders

| placeholder | description |
| --- | --- |
| `title` | Paper title (from Zotero, or derived from the PDF name). |
| `citekey` | Zotero citekey (empty if missing). |
| `year` | Publication year. |
| `authors` | Author string. |
| `venue` | Venue or journal name. |
| `doi` | DOI. |
| `url` | URL. |
| `source_url` | Derived URL from Zotero metadata. |
| `zotero_select_uri` | Zotero select URI. |
| `pdf_path` | PDF file path. |
| `tags` | Tags as a comma-separated string. |
| `tags_list` | Tags list stringified. |
| `abstract` | Abstract text. |
| `zotero_abstract` | Abstract from Zotero (same as `abstract`). |
| `generated_summary` | LLM summary (when enabled). |
| `highlights` | Highlights. |
| `zotero_highlights` | Highlights from Zotero annotations. |
| `zotomatic_summary_status` | Summary status (`pending`, etc.). |
| `zotomatic_summary_mode` | Summary mode (`quick` / `standard` / `deep`). |
| `zotomatic_tag_status` | Tag status (`pending`, etc.). |
| `zotomatic_last_updated` | Last updated time (ISO 8601). |
| `slug80` | 80-character slug from `title` / `citekey` / `year`. |
| `slug40` | 40-character slug from `title` / `citekey` / `year`. |
