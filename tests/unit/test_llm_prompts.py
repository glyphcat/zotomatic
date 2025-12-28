from __future__ import annotations

from zotomatic.llm import prompts


def test_get_prompt_has_system_and_user() -> None:
    template = prompts.get_prompt("summary_quick")
    assert "system" in template
    assert "user" in template


def test_get_prompt_tags_template() -> None:
    template = prompts.get_prompt("tags")
    assert "{tags_max}" in template["user"]
