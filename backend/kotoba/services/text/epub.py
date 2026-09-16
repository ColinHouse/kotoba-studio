"""Parse EPUB light novels into chapters and sentences.

EPUB is a zip: ``META-INF/container.xml`` points at the OPF package, whose
``spine`` gives the reading order of the XHTML documents — never the file names.
Only the standard library is used (``zipfile`` + ``xml.etree``), so importing a
book adds no dependency.

Ruby is handled deliberately: ``<rt>`` readings are extracted next to the base
text instead of being concatenated into it, because
``食べ物<rt>たべもの</rt>`` becoming ``食べ物たべもの`` would wreck tokenization.
The persisted sentence keeps its reading as ``食べ物（たべもの）``.

Sentence boundaries follow Japanese punctuation: ``。！？`` end a sentence, the
closing ``」』`` stays with the sentence it closes, and an ender inside quotes
does not split — ``「そうか。すぐ行く」`` must not break in the middle.
``……`` is not a sentence end.
"""

from __future__ import annotations

import posixpath
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO
from urllib.parse import unquote
from xml.etree import ElementTree

from kotoba.core.errors import ApiError

_CONTAINER = "META-INF/container.xml"
_CHAPTER_MEDIA = {"application/xhtml+xml", "text/html"}
_SKIPPED_TAGS = {"script", "style", "head", "title", "rt", "rp"}
_BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "body",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
_END = "。！？"
_OPEN_QUOTES = "「『"
_CLOSE_QUOTES = "」』"
_WHITESPACE = re.compile(r"\s+")
_PARAGRAPH_SEPARATOR = "\n"


@dataclass(slots=True)
class Ruby:
    base: str
    reading: str
    position: int


@dataclass(slots=True)
class EpubSentence:
    text: str
    raw_text: str
    start: int
    end: int


@dataclass(slots=True)
class EpubChapter:
    number: int
    text: str
    sentences: list[EpubSentence]
    ruby: list[Ruby]


def validate_epub(source: BinaryIO) -> int:
    """Parse every spine document once so a broken chapter fails before import.

    Returns the number of chapter documents; raises ``bad_epub`` otherwise.
    """
    with _zip(source) as archive:
        opf_path = _opf_path(archive)
        paths = _spine_paths(archive, opf_path)
        for path in paths:
            _parse(_read(archive, path), path)
    return len(paths)


def iter_chapters(source: BinaryIO) -> Iterator[EpubChapter]:
    """Yield chapters in spine order, one at a time so memory stays bounded."""
    with _zip(source) as archive:
        opf_path = _opf_path(archive)
        number = 0
        for path in _spine_paths(archive, opf_path):
            paragraphs = _paragraphs(_read(archive, path), path)
            text, sentences, ruby = _chapter(paragraphs)
            if not sentences:
                continue
            number += 1
            yield EpubChapter(number=number, text=text, sentences=sentences, ruby=ruby)


def _zip(source: BinaryIO) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(source)
    except zipfile.BadZipFile as exc:
        raise _bad("不是有效的 EPUB（zip）文件") from exc


def _read(archive: zipfile.ZipFile, path: str) -> bytes:
    try:
        return archive.read(path)
    except KeyError as exc:
        raise _bad(f"EPUB 里缺少文件：{path}") from exc


def _parse(raw: bytes, where: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise _bad(f"{where} 不是有效的 XHTML") from exc


def _opf_path(archive: zipfile.ZipFile) -> str:
    root = _parse(_read(archive, _CONTAINER), _CONTAINER)
    for element in root.iter():
        if _local(element.tag) == "rootfile":
            path = element.get("full-path")
            if path:
                return path
    raise _bad("container.xml 里没有 rootfile")


def _spine_paths(archive: zipfile.ZipFile, opf_path: str) -> list[str]:
    root = _parse(_read(archive, opf_path), opf_path)
    items: dict[str, tuple[str, str]] = {}
    for element in root.iter():
        if _local(element.tag) != "item":
            continue
        item_id, href = element.get("id"), element.get("href")
        if item_id and href:
            items[item_id] = (href, element.get("media-type", ""))
    paths: list[str] = []
    for element in root.iter():
        if _local(element.tag) != "itemref":
            continue
        if element.get("linear") == "no":
            continue
        idref = element.get("idref")
        item = items.get(idref) if idref else None
        if item is None:
            raise _bad(f"spine 引用了不存在的 idref：{idref}")
        href, media_type = item
        if media_type not in _CHAPTER_MEDIA:
            continue
        paths.append(posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), unquote(href))))
    if not paths:
        raise _bad("spine 里没有可读章节")
    return paths


def _chapter(
    paragraphs: list[tuple[str, list[Ruby]]],
) -> tuple[str, list[EpubSentence], list[Ruby]]:
    pieces: list[str] = []
    sentences: list[EpubSentence] = []
    ruby: list[Ruby] = []
    offset = 0
    for text, marks in paragraphs:
        if pieces:
            offset += len(_PARAGRAPH_SEPARATOR)
        sentences.extend(_split_sentences(text, offset, marks))
        pieces.append(text)
        ruby.extend(marks)
        offset += len(text)
    return _PARAGRAPH_SEPARATOR.join(pieces), sentences, ruby


def _split_sentences(text: str, base: int, ruby: list[Ruby]) -> list[EpubSentence]:
    """Cut at 。！？, keeping the closing quote with the sentence it closes.

    An ender inside quotes only ends the sentence when the quote closes right
    after it (``「そうか。」``); ``「そうか。すぐ行く」`` stays whole.
    """
    out: list[EpubSentence] = []
    depth = 0
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in _OPEN_QUOTES:
            depth += 1
        elif char in _CLOSE_QUOTES:
            depth = max(depth - 1, 0)
        elif char in _END:
            end = index + 1
            while end < len(text) and text[end] in _END:
                end += 1
            quotes = 0
            while end + quotes < len(text) and text[end + quotes] in _CLOSE_QUOTES:
                quotes += 1
            if depth == 0 or quotes:
                end += quotes
                depth = max(depth - quotes, 0)
                out.append(_sentence(text, start, end, base, ruby))
                start = end
                index = end
                continue
        index += 1
    if start < len(text):
        out.append(_sentence(text, start, len(text), base, ruby))
    return out


def _sentence(text: str, start: int, end: int, base: int, ruby: list[Ruby]) -> EpubSentence:
    raw = text[start:end]
    stripped = raw.strip()
    begin = start + len(raw) - len(raw.lstrip())
    finish = begin + len(stripped)
    marks = [mark for mark in ruby if begin <= mark.position < finish]
    return EpubSentence(
        text=stripped,
        raw_text=_annotate(stripped, begin, marks),
        start=base + begin,
        end=base + finish,
    )


def _annotate(text: str, begin: int, marks: list[Ruby]) -> str:
    if not marks:
        return text
    out: list[str] = []
    cursor = 0
    for mark in marks:
        offset = mark.position - begin
        out.append(text[cursor:offset])
        out.append(mark.base)
        if mark.reading:
            out.append(f"（{mark.reading}）")
        cursor = offset + len(mark.base)
    out.append(text[cursor:])
    return "".join(out)


def _paragraphs(raw: bytes, where: str) -> list[tuple[str, list[Ruby]]]:
    root = _parse(raw, where)
    paragraphs: list[tuple[str, list[Ruby]]] = []
    buffer: list[str] = []
    pairs: list[tuple[str, str]] = []

    def flush() -> None:
        text = _WHITESPACE.sub(" ", "".join(buffer)).strip()
        if text:
            paragraphs.append((text, _locate(text, pairs)))
        buffer.clear()
        pairs.clear()

    def walk(element: ElementTree.Element) -> None:
        tag = _local(element.tag)
        if tag in _SKIPPED_TAGS:
            return
        if tag in _BLOCK_TAGS:
            flush()
        if tag == "ruby":
            base, reading = _ruby(element)
            if base:
                buffer.append(base)
                if reading:
                    pairs.append((base, reading))
        else:
            if element.text:
                buffer.append(element.text)
            for child in element:
                walk(child)
                if child.tail:
                    buffer.append(child.tail)
        if tag in _BLOCK_TAGS:
            flush()

    walk(root)
    flush()
    return paragraphs


def _ruby(element: ElementTree.Element) -> tuple[str, str]:
    base: list[str] = []
    reading: list[str] = []
    if element.text:
        base.append(element.text)
    for child in element:
        tag = _local(child.tag)
        if tag == "rt":
            if child.text:
                reading.append(child.text)
        elif tag != "rp":
            child_base, child_reading = _ruby(child)
            base.append(child_base)
            reading.append(child_reading)
        if child.tail:
            base.append(child.tail)
    return _WHITESPACE.sub("", "".join(base)), _WHITESPACE.sub("", "".join(reading))


def _locate(text: str, pairs: list[tuple[str, str]]) -> list[Ruby]:
    marks: list[Ruby] = []
    cursor = 0
    for base, reading in pairs:
        position = text.find(base, cursor)
        if position < 0:
            position = text.find(base)
        if position < 0:
            continue
        marks.append(Ruby(base=base, reading=reading, position=position))
        cursor = position + len(base)
    return marks


def _local(tag: object) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].lower()


def _bad(message: str) -> ApiError:
    return ApiError("bad_epub", message)
