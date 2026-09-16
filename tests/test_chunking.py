from pathlib import Path

import pytest

from chunking import md_header_chunk


def test_md_header_chunk_splits_on_headers(tmp_path: Path):
    markdown = tmp_path / "doc.md"
    markdown.write_text(
        "Hello World\n"
        "\n"
        "# Test Header\n"
        "\n"
        "test text\n"
        "test text 2\n"
        "\n"
        "# Test Header 2\n",
        encoding="utf-8",
    )

    chunks = md_header_chunk(str(markdown))

    assert chunks == [
        "Hello World\n\n",
        "# Test Header\n\ntest text\ntest text 2\n\n",
        "# Test Header 2\n",
    ]


def test_md_header_chunk_starts_with_header(tmp_path: Path):
    markdown = tmp_path / "doc.md"
    markdown.write_text(
        "# Title\n"
        "intro\n"
        "## Nested\n"
        "details\n",
        encoding="utf-8",
    )

    chunks = md_header_chunk(str(markdown))

    assert chunks == [
        "# Title\nintro\n",
        "## Nested\ndetails\n",
    ]


def test_md_header_chunk_no_headers_is_one_chunk(tmp_path: Path):
    markdown = tmp_path / "doc.md"
    markdown.write_text("just prose\nand more\n", encoding="utf-8")

    assert md_header_chunk(str(markdown)) == ["just prose\nand more\n"]


def test_md_header_chunk_empty_file(tmp_path: Path):
    markdown = tmp_path / "empty.md"
    markdown.write_text("", encoding="utf-8")

    assert md_header_chunk(str(markdown)) == []


def test_md_header_chunk_rejects_missing_path(tmp_path: Path):
    missing = tmp_path / "missing.md"
    with pytest.raises(ValueError, match="does not exist"):
        md_header_chunk(str(missing))


def test_md_header_chunk_rejects_directory(tmp_path: Path):
    directory = tmp_path / "notes.md"
    directory.mkdir()
    with pytest.raises(ValueError, match="is not a file"):
        md_header_chunk(str(directory))


def test_md_header_chunk_rejects_non_markdown(tmp_path: Path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("# Should not be read\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Not a markdown file"):
        md_header_chunk(str(text_file))
    assert text_file.read_text(encoding="utf-8") == "# Should not be read\n"
