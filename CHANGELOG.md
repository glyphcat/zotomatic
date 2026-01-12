# Changelog

## Unreleased

## 0.2.1
- Added `--version` to print the installed Zotomatic version.
- Added version lookup helper (`__version__`) for the CLI.
- Documented version check in configuration references (EN/JA).
- Reworked `config show` LLM output to group settings and display all providers.

## 0.2.0
- Added Gemini support as an LLM provider alongside ChatGPT.
- Introduced a new LLM configuration schema (`[llm]` and `[llm.providers.*]`).
- Added `llm set` and `config migrate` commands for LLM and config updates.
- Updated default LLM models and output token limits for better summaries.
- Added `chatgpt` as an alias for the `openai` LLM provider.
- Added `scan --summary-mode` to override summary detail per run without changing config.

## 0.1.1
- Improve Quick Start
- Fix documentation links

## 0.1.0
- Initial release.
