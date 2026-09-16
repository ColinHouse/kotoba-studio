"""Sentence analysis: tokens + expression spans + dictionary candidates + learner state."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.models import Encounter, Line, Term
from kotoba.services.dictionary import lookup
from kotoba.services.dictionary.yomitan import frequency
from kotoba.services.jp import contractions, expressions
from kotoba.services.jp.tokenizer import tokenize

CANDIDATES_PER_TOKEN = 3


def _term_state(db: Session, keys: list[str]) -> dict[str, dict]:
    """headword → {term_id, known_status, encounter_count} for any of the given headwords."""
    if not keys:
        return {}
    rows = db.execute(
        select(Term.id, Term.headword, Term.known_status).where(Term.headword.in_(keys))
    ).all()
    out: dict[str, dict] = {}
    for term_id, headword, status in rows:
        count = db.scalar(select(Encounter.id).where(Encounter.term_id == term_id).limit(1))
        out.setdefault(
            headword,
            {"term_id": term_id, "known_status": status, "encountered": count is not None},
        )
    return out


def analyze_text(db: Session, text: str) -> dict:
    tokens = tokenize(text)
    index = expressions.get_index(db)
    spans = expressions.group(tokens, index.readings_for)
    token_dicts = []
    for t in tokens:
        d = t.to_dict()
        d["candidates"] = (
            [c.to_dict() for c in lookup.candidates_for_token(db, t, CANDIDATES_PER_TOKEN)]
            if t.is_content
            else []
        )
        token_dicts.append(d)
    span_dicts = []
    for s in spans:
        d = s.to_dict()
        d["candidates"] = [c.to_dict() for c in lookup.lookup(db, s.matched_form, 3)]
        span_dicts.append(d)
    return {
        "text": text,
        "tokens": token_dicts,
        "spans": span_dicts,
        "contractions": contractions.find_in_tokens([t.surface for t in tokens]),
    }


def attach_learner_state(db: Session, analysis: dict) -> dict:
    keys: list[str] = []
    for t in analysis["tokens"]:
        for k in (t["base"], t["lemma"], t["surface"]):
            if k not in keys:
                keys.append(k)
    for s in analysis["spans"]:
        if s["matched_form"] not in keys:
            keys.append(s["matched_form"])
    state = _term_state(db, keys)
    ranks = frequency.ranks_for(
        db,
        [
            (t["base"] or t["lemma"] or t["surface"], t["reading_base"] or t["reading"])
            for t in analysis["tokens"]
        ],
    )
    for t, rank in zip(analysis["tokens"], ranks, strict=True):
        t["frequency_rank"] = rank
    for t in analysis["tokens"]:
        hit = state.get(t["base"]) or state.get(t["lemma"]) or state.get(t["surface"])
        t["term_id"] = hit["term_id"] if hit else None
        t["known_status"] = hit["known_status"] if hit else None
        t["encountered"] = bool(hit and hit["encountered"])
    for s in analysis["spans"]:
        hit = state.get(s["matched_form"])
        s["term_id"] = hit["term_id"] if hit else None
        s["known_status"] = hit["known_status"] if hit else None
    return analysis


def analyze_line(db: Session, line: Line, force: bool = False) -> dict:
    cached = json.loads(line.tokens_json) if line.tokens_json and not force else None
    if cached is None or cached.get("text") != line.text:
        cached = analyze_text(db, line.text)
        line.tokens_json = json.dumps(cached, ensure_ascii=False)
        db.commit()
    result = json.loads(json.dumps(cached))  # copy before mutating with learner state
    result["line_id"] = line.id
    return attach_learner_state(db, result)
