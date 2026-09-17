"""A work's page-located lines, grouped the way the manga reader displays them."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.models import Card, Encounter, Line
from kotoba.schemas.lines import line_locator


@dataclass(slots=True)
class PageBlock:
    line_id: int
    text: str
    box: list[float]
    status: str
    encounter_count: int
    card_count: int


@dataclass(slots=True)
class PageGroup:
    page: int
    image: str | None
    blocks: list[PageBlock]


def source_pages(db: Session, source_id: int) -> list[PageGroup]:
    """Page groups in reading order: page ascending, blocks by `ord`.

    Only lines carrying a page locator belong to the reader; game captures and
    subtitles are skipped. The page image is taken from the first line on the
    page that has a screenshot, so a text-only import simply has none.
    """
    cards = (
        select(Encounter.line_id.label("line_id"), func.count(Card.id).label("cards"))
        .join(Card, Card.primary_encounter_id == Encounter.id)
        .group_by(Encounter.line_id)
        .subquery()
    )
    rows = db.execute(
        select(Line, func.count(Encounter.id), func.coalesce(cards.c.cards, 0))
        .outerjoin(Encounter, Encounter.line_id == Line.id)
        .outerjoin(cards, cards.c.line_id == Line.id)
        .where(Line.source_id == source_id)
        .group_by(Line.id)
        .order_by(Line.ord.is_(None), Line.ord.asc(), Line.id.asc())
    ).all()

    pages: dict[int, PageGroup] = {}
    for line, encounters, card_count in rows:
        locator = line_locator(line)
        if not locator or locator.get("kind") != "page":
            continue
        page_no = locator.get("page")
        box = locator.get("box")
        if not isinstance(page_no, int) or not _valid_box(box):
            continue
        group = pages.setdefault(page_no, PageGroup(page=page_no, image=None, blocks=[]))
        if group.image is None and line.screenshot_path:
            group.image = line.screenshot_path
        group.blocks.append(
            PageBlock(
                line_id=line.id,
                text=line.text,
                box=[float(value) for value in box],
                status=line.status,
                encounter_count=encounters,
                card_count=card_count,
            )
        )
    return [pages[page_no] for page_no in sorted(pages)]


def _valid_box(box: object) -> bool:
    return (
        isinstance(box, list)
        and len(box) == 4
        and all(isinstance(value, (int, float)) for value in box)
    )
