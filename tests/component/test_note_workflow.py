from __future__ import annotations

from pathlib import Path

from zotomatic.logging import get_logger
from zotomatic.llm.types import LLMTagResult, LLMSummaryMode, LLMSummaryResult
from zotomatic.note.builder import NoteBuilder
from zotomatic.note.types import NoteBuilderConfig, NoteBuilderContext, NoteWorkflowConfig, NoteWorkflowContext
from zotomatic.note.workflow import NoteWorkflow
from zotomatic.repositories import NoteRepository, NoteRepositoryConfig


class FakeLLMClient:
    def __init__(self, summary: str = "Summary", tags: tuple[str, ...] = ("tagA",)) -> None:
        self.summary = summary
        self.tags = tags

    def generate_summary(self, _context):
        return LLMSummaryResult(mode=LLMSummaryMode.QUICK, summary=self.summary, raw_response={})

    def generate_tags(self, _context):
        return LLMTagResult(tags=self.tags, raw_response={})


def _make_builder(tmp_path: Path) -> NoteBuilder:
    template = tmp_path / "note.md"
    template.write_text("---\ntitle: {title}\n---\n{generated_summary}\n", encoding="utf-8")
    repo = NoteRepository(NoteRepositoryConfig(root_dir=tmp_path / "notes"))
    return NoteBuilder(
        repository=repo,
        config=NoteBuilderConfig(template_path=template, filename_pattern="{{ citekey }}"),
    )


def test_update_pending_note(tmp_path: Path) -> None:
    builder = _make_builder(tmp_path)
    repo = builder._repository
    logger = get_logger("zotomatic.test", False)
    llm_client = FakeLLMClient()
    workflow = NoteWorkflow(
        note_builder=builder,
        note_repository=repo,
        llm_client=llm_client,
        config=NoteWorkflowConfig(summary_enabled=True, tag_enabled=True, summary_mode="quick"),
        llm_usage=None,
        logger=logger,
    )

    context = NoteBuilderContext(title="Title", citekey="CITE", pdf_path="/tmp/file.pdf")
    note = builder.generate_note(context)

    updated = workflow.update_pending_note(
        NoteWorkflowContext(builder_context=context, existing_path=note.path)
    )
    assert updated is True
    text = note.path.read_text(encoding="utf-8")
    assert "Summary" in text
    assert "zotomatic_summary_status: done" in text
    assert "zotomatic_tag_status: done" in text


def test_update_pdf_path_if_changed(tmp_path: Path) -> None:
    builder = _make_builder(tmp_path)
    repo = builder._repository
    logger = get_logger("zotomatic.test.pdf", False)
    workflow = NoteWorkflow(
        note_builder=builder,
        note_repository=repo,
        llm_client=None,
        config=NoteWorkflowConfig(summary_enabled=False, tag_enabled=False),
        llm_usage=None,
        logger=logger,
    )

    context = NoteBuilderContext(title="Title", citekey="CITE", pdf_path="/tmp/file.pdf")
    note = builder.generate_note(context)

    updated = workflow.update_pdf_path_if_changed(
        NoteWorkflowContext(builder_context=context.with_updates(pdf_path="/tmp/other.pdf"), existing_path=note.path)
    )
    assert updated is True
    text = note.path.read_text(encoding="utf-8")
    assert "pdf_local: /tmp/other.pdf" in text
