# Zotomatic

Zotomatic is a CLI tool that generates Markdown research notes from PDFs using user-defined templates, Zotero metadata, and extracted text.  

Zotomatic は、研究論文の PDF から Zotero の書誌情報や本文抽出結果をもとに、
ユーザー定義テンプレートに従った Markdown 形式の研究ノートを自動生成する CLI ツールです。  
[日本語版READMEはこちら](README.ja.md)  

---

## Quick Start

[Start Guide](docs/en/getting-started.md)

### Install

```bash
pip install zotomatic
zotomatic init --pdf-dir ./papers  # Directory for PDFs
```

### Generate notes from a PDF file

Generate a Markdown note from a specific PDF in any directory.  
`pdf_dir` is not required.

```bash
zotomatic scan --path ./papers/sample.pdf
```

### Batch process PDFs under the configured directory

Process all PDFs under the configured directory.  
`pdf_dir` is required.

```bash
zotomatic scan --once
```

### Watch the configured directory for new PDFs

Watch the configured directory and generate notes whenever a PDF is added.  
`pdf_dir` is required.

```bash
zotomatic scan --watch
```

---

## Overview

Zotomatic is a CLI tool that starts from research PDFs, uses bibliographic information and extracted text, and generates Markdown notes based on user-defined templates.

For PDFs managed in Zotero, Zotomatic can fetch metadata such as authors, title, and abstract to produce notes enriched with bibliographic details. It can also generate minimal notes for PDFs outside Zotero.

Zotomatic can optionally integrate with an LLM to generate summaries and tags in a specified language and insert the results into notes.  
Note: Output quality and accuracy depend on the LLM.

Notes are plain Markdown files, and templates are fully user-defined. You can use them with any editor or knowledge tool, including Obsidian.

---

## Key Features

- **Automatic Markdown note generation from research PDFs**  
  Avoid manual note taking and output reusable research notes in Markdown.

- **Automatic metadata retrieval from Zotero-managed PDFs**  
  Pull authors, title, abstract, and other bibliographic data from Zotero and insert them into notes.

- **Support for PDFs outside Zotero**  
  Generate minimal, structured notes even when PDFs are not registered in Zotero.

- **Best-effort completion for missing metadata**  
  If Zotero metadata is incomplete, Zotomatic attempts to fill missing fields from PDF text.  
  Note: Completion runs only for Zotero-managed PDFs.

- **Flexible, user-defined templates**  
  Customize headings and sections to match your workflow.

- **Optional LLM summaries and tags (language-selectable)**  
  Generate summaries and tags via LLM when enabled (default output is Japanese with other languages available).

- **Multiple scan modes**  
  Use watch, once, or path mode to fit your workflow.

---

## Installation

```bash
pip install zotomatic
```

---

## Use Cases

- **Auto-generate notes from PDFs saved in the browser**  
  Save a PDF via Zotero Connector and run `scan --watch` for real-time note creation.
- **Batch-generate notes for an existing library**  
  Run `scan --once` to process everything under `pdf_dir`.
- **Spot-process PDFs outside Zotero**  
  Use `scan --path` for quick, file-specific note generation.
- **Auto-insert summaries and tags (optional)**  
  With an API key, generate summaries and tags in a chosen language (ChatGPT and Gemini supported).

If you want Zotero metadata, keep the Zotero desktop app running.

See `docs/en/getting-started.md` for step-by-step instructions.

---

## Documentation

- [Index](docs/en/index.md)
- [Start Guide](docs/en/getting-started.md)
- [Configuration Reference](docs/en/configuration.md)
- [CLI Reference](docs/en/cli.md)

---

## Roadmap

- Support additional LLM providers

Note: Roadmap items and timelines may change.

---

## Notes

- Zotomatic is a research support tool and does not guarantee the accuracy of generated summaries or tags.
- Always verify results against the original paper before citing.

---

## License

MIT License

---

## Support and Feedback

Please use GitHub Issues for bug reports.

This is a personal project, so not all issues or pull requests can be addressed. Pull requests are not accepted at this time.
