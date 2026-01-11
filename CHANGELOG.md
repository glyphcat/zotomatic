# Changelog

## 0.1.0
- Initial release.

## Unreleased
- Added Gemini support as an LLM provider alongside ChatGPT.
- Introduced a new LLM configuration schema (`[llm]` and `[llm.providers.*]`).
- Added `llm set` and `config migrate` commands for LLM and config updates.
- Updated default LLM models and output token limits for better summaries.
- Added `chatgpt` as an alias for the `openai` LLM provider.
- Added `scan --summary-mode` to override summary detail per run without changing config.
