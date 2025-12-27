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


def update_frontmatter_value(
    text: str, key: str, value: str
) -> tuple[str, bool]:
    if not text.startswith("---"):
        return text, False
    lines = text.splitlines()
    try:
        end_idx = lines[1:].index("---") + 1
    except ValueError:
        return text, False

    target_prefix = f"{key}:"
    changed = False
    for idx in range(1, end_idx):
        line = lines[idx]
        stripped = line.lstrip()
        if not stripped.startswith(target_prefix):
            continue
        prefix = line[: len(line) - len(stripped)]
        current = stripped.split(":", 1)[1].strip()
        if current == value:
            return text, False
        lines[idx] = f"{prefix}{key}: {value}"
        changed = True
        break

    if not changed:
        lines.insert(end_idx, f"{key}: {value}")
        changed = True

    updated = "\n".join(lines)
    if text.endswith("\n"):
        updated += "\n"
    return updated, True
