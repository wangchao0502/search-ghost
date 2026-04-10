"""Unit tests for the Markdown parser."""

from search_ghost.layers.processing.parsers.markdown import MarkdownParser


def test_plain_text():
    parser = MarkdownParser()
    result = parser.parse(b"Hello world", "test.txt")
    assert result == "Hello world"


def test_strips_html():
    parser = MarkdownParser()
    result = parser.parse(b"<b>Bold</b> text", "test.html")
    assert "<b>" not in result
    assert "Bold" in result


def test_normalises_crlf():
    parser = MarkdownParser()
    result = parser.parse(b"line1\r\nline2\r\nline3", "test.txt")
    assert "\r" not in result
    assert result == "line1\nline2\nline3"


def test_strips_surrounding_whitespace():
    parser = MarkdownParser()
    result = parser.parse(b"\n\n  content  \n\n", "test.md")
    assert result == "content"
