---
# Required keys (do not remove):
# - citekey
# - pdf_local
# - zotomatic_summary_status
# - zotomatic_tag_status
# - zotomatic_summary_mode
# - tags
#
# Keys not listed above are optional and safe to edit/remove.
# Keep template variables like {{title}}; removing them leaves blanks.
type: paper
title: "{title}"
citekey: {citekey}
year: {year}
authors: {authors}
venue: {venue}
doi: {doi}
url: {url}
source_url: {source_url}
zotero: {zotero_select_uri}
pdf_local: {pdf_path}
status: unread
tags: [{tags}]
# Zotomatic (auto-managed)
# summary_status: pending | done
zotomatic_summary_status: {zotomatic_summary_status}
# summary_mode: quick | standard | deep (mode used when summary was generated)
zotomatic_summary_mode: {zotomatic_summary_mode}
# tag_status: pending | done
zotomatic_tag_status: {zotomatic_tag_status}
zotomatic_last_updated: {zotomatic_last_updated}
---
<!-- Placeholders:
{{generated_summary}} = LLM-generated summary
{{zotero_abstract}}   = Abstract fetched from Zotero metadata
{{zotero_highlights}} = Highlights/comments fetched from Zotero annotations
-->

> [!summary] AI-generated Summary
> {generated_summary}

## Abstract
{zotero_abstract}

## Highlights / Notes
{zotero_highlights}

## Key Points
