from __future__ import annotations


def parse_frontmatter(text: str) -> dict[str, object]:
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    try:
        end_idx = lines[1:].index("---") + 1
    except ValueError:
        return {}
    meta: dict[str, object] = {}
    for line in lines[1:end_idx]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta


def parse_tags(value: str) -> tuple[str, ...]:
    stripped = value.strip()
    if not stripped.startswith("[") or not stripped.endswith("]"):
        return ()
    raw = stripped[1:-1].strip()
    if not raw:
        return ()
    tags: list[str] = []
    for part in raw.split(","):
        item = part.strip().strip('"').strip("'")
        if item:
            tags.append(item)
    return tuple(tags)


def extract_summary_block(text: str) -> str:
    lines = text.splitlines()
    summary_idx = None
    for idx, line in enumerate(lines):
        if "[!summary]" in line:
            summary_idx = idx
            break
    if summary_idx is None:
        return ""
    summary_lines: list[str] = []
    for line in lines[summary_idx + 1 :]:
        if not line.startswith(">"):
            break
        summary_lines.append(line.lstrip("> ").rstrip())
    return "\n".join(summary_lines).strip()
