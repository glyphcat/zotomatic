from __future__ import annotations

from pathlib import Path

from zotomatic.note.builder import NoteBuilder
from zotomatic.note.types import NoteBuilderConfig, NoteBuilderContext
from zotomatic.repositories import NoteRepository, NoteRepositoryConfig


def test_note_builder_generate_note(tmp_path: Path) -> None:
    template = tmp_path / "note.md"
    template.write_text("---\n---\n{title}\n{generated_summary}\n", encoding="utf-8")
    repo = NoteRepository(NoteRepositoryConfig(root_dir=tmp_path / "notes"))
    builder = NoteBuilder(
        repository=repo,
        config=NoteBuilderConfig(template_path=template, filename_pattern="{{ citekey }}"),
    )
    context = NoteBuilderContext(
        title="Title",
        citekey="CITE",
        year="2024",
        tags=("tag1",),
        generated_tags=("tag2",),
        generated_summary="Summary",
        pdf_path="/tmp/file.pdf",
    )
    note = builder.generate_note(context)
    assert note.path.exists()
    rendered = note.path.read_text(encoding="utf-8")
    assert "citekey: CITE" in rendered
    assert "zotomatic_summary_status" in rendered
    assert "tags:" in rendered
    assert "Summary" in rendered


def test_note_builder_output_path_pattern(tmp_path: Path) -> None:
    template = tmp_path / "note.md"
    template.write_text("{title}", encoding="utf-8")
    repo = NoteRepository(NoteRepositoryConfig(root_dir=tmp_path / "notes"))
    builder = NoteBuilder(
        repository=repo,
        config=NoteBuilderConfig(template_path=template, filename_pattern="{{ year }}/{{ citekey }}"),
    )
    context = NoteBuilderContext(title="Title", citekey="Key", year="2020")
    note = builder.generate_note(context)
    assert note.path.suffix == ".md"
    assert "2020" in str(note.path)
