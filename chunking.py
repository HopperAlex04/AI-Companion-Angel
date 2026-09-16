from pathlib import Path

_MARKDOWN_SUFFIXES = {".md", ".markdown"}


def md_header_chunk(path: str) -> list[str]:
    file_path = Path(path)
    if file_path.suffix.lower() not in _MARKDOWN_SUFFIXES:
        raise ValueError(f"Not a markdown file: {path}")
    if not file_path.exists():
        raise ValueError(f"Markdown path does not exist: {path}")
    if not file_path.is_file():
        raise ValueError(f"Markdown path is not a file: {path}")

    chunks = []
    i = 0
    first_chunk = False
    with file_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("#"):
            if first_chunk:
                i += 1
            else:
                first_chunk = True
            chunks.append(line)
        else:
            if i == 0:
                if first_chunk:
                    chunks[i] += line
                else:
                    chunks.append(line)
                    first_chunk = True
            else:
                chunks[i] += line
    return chunks
