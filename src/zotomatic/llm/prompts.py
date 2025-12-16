"""Default prompt templates for LLM interactions."""

from __future__ import annotations

from typing import Literal, Mapping, NotRequired, TypedDict, cast


class PromptDict(TypedDict):
    system: str
    user: str
    description: NotRequired[str]


_PROMPTS: dict[str, PromptDict] = {
    "summary_quick": {
        "system": (
            "Your role is a research assistant. "
            "You must always provide concise and accurate summaries in {language}."
        ),
        "user": (
            "The following is an excerpt from an academic paper (mainly the abstract/introduction). "
            "Please create a 3–4 sentence summary in {language}.\n"
            "Constraints: Preserve proper nouns and key numerical values. Clearly express causal relationships while avoiding redundancy. Do not use bullet points.\n"
            "---\n"
            "{abstract}"
        ),
    },
    "summary_standard": {
        "system": (
            "You are a research assistant. "
            "Always return scholarly and appropriately balanced combined summaries in {language}."
        ),
        "user": (
            "The following is source material for summarizing an academic paper."
            "It combines the abstract and excerpts from the introductions of key sections.\n"
            "Requirement: Create a combined summary in {language}, 5–6 sentences long, that clearly conveys the background, methodology, experiments, results, discussion, and limitations.\n"
            "---\n"
            "[Abstract]\n"
            "{abstract}\n\n"
            "[Section Samples]\n"
            "{section_samples}"
        ),
    },
    "summary_deep_chunk": {
        "system": (
            "You are a research assistant. Always provide precise, faithful summaries in {language}."
        ),
        "user": (
            "The following is a section of a paper (chunk {chunk_index}/{chunk_count}). "
            "Summarize it in {language} in {sentences_min}–{sentences_max} sentences without losing meaning.\n"
            "Constraints: Preserve key numerical values and proper nouns. Avoid redundant rephrasing.\n"
            "---\n"
            "{chunk_text}"
        ),
    },
    "summary_deep_reduce": {
        "system": (
            "You are a research assistant. Always return scholarly and appropriately balanced combined summaries in {language}."
        ),
        "user": (
            "Below are the per-chunk summaries of a paper. Taking a global view, produce a comprehensive summary in {language} "
            "of {sentences_min}–{sentences_max} sentences.\n"
            "Requirements: Clearly cover the research problem, methods, data, main results, limitations, and contributions. "
            "Eliminate duplication across chunks and make causal relationships explicit. No bullet points.\n"
            "---\n"
            "[Abstract]\n"
            "{abstract}\n\n"
            "[Chunk Summaries]\n"
            "{chunk_summaries}"
        ),
    },
    "tags": {
        "system": "You suggest topical tags for knowledge management.",
        "user": (
            "From the following paper title and abstract, return up to {tags_max} short tags, comma-separated. Tags may be in {language}, in English, or mixed.\n"
            "Constraints: Prioritize specific terms such as technology names, domains, and task names. Each tag must be 1–3 words; spaces and hyphens are allowed. "
            "Do not prefix tags with #. No explanations.\n"
            "---\n"
            "Title: {title}\n"
            "Abstract: {abstract}"
        ),
    },
}


def get_prompt(
    template_key: Literal[
        "summary_quick",
        "summary_standard",
        "summary_deep_chunk",
        "summary_deep_reduce",
        "tags",
    ],
) -> dict[str, str]:
    """
    Return the prompt templates for the given key.

    Currently available templates:
        - summary_quick:
            Generate a quick summary **using only the abstract**.
            Required variables: {language}, {abstract}
        - summary_standard
            Generate a comprehensive summary **using section headings and sample texts**.
            Required variables: {language}, {abstract}, {section_samples}
        - summary_deep_chunk
            Deep summarization for each text chunk.
            Required variables: {language}, {chunk_index}, {chunk_count}, {chunk_text}
        - summary_deep_reduce
            Final reduction step for deep summaries.
            Required variables: {language}, {abstract}, {chunk_summaries}
        - tags
            Generate keyword-style tags.
            Required variables: {language}, {abstract}, {title}
    """

    return cast(dict[str, str], _PROMPTS[template_key])


def build_summary_quick(language: str, abstract: str) -> dict[str, str]:
    template = get_prompt("summary_quick")
    return {}


def build_summary_standard(): ...


def build_summary_deep_chunk(): ...


def build_summary_deep_reduce(): ...


def build_tags(): ...
