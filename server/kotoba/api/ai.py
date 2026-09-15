"""AI explanations (optional; never required for capture or review)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import Encounter, Line, LlmCall, utcnow
from kotoba.services import learning
from kotoba.services.ai import llm, prompts

router = APIRouter(prefix="/ai", tags=["ai"])


class ExplainIn(BaseModel):
    encounter_id: int
    force: bool = False


def _prior_lines(db: Session, line: Line, limit: int = 3) -> list[str]:
    if line.session_id is None:
        return []
    rows = db.scalars(
        select(Line.text)
        .where(
            Line.session_id == line.session_id,
            Line.captured_at <= line.captured_at,
            Line.id < line.id,
        )
        .order_by(Line.captured_at.desc(), Line.id.desc())
        .limit(limit)
    ).all()
    return list(reversed(rows))


@router.post("/explain")
def explain(body: ExplainIn, request: Request, db: Session = Depends(get_db)) -> dict:
    enc = db.get(Encounter, body.encounter_id)
    if enc is None:
        raise ApiError("not_found", f"encounter {body.encounter_id} not found", 404)
    if enc.ai_explanation_json and not body.force:
        return {"explanation": json.loads(enc.ai_explanation_json), "cached": True}
    line = db.get(Line, enc.line_id)
    term = enc.term
    glosses = [s.gloss_zh or s.gloss_en or "" for s in term.senses if (s.gloss_zh or s.gloss_en)]
    system, user = prompts.explain_prompt(
        term.headword,
        term.reading,
        enc.surface,
        line.text,
        _prior_lines(db, line),
        glosses,
        learning.homograph_trap(term.headword),
    )
    transport = getattr(request.app.state, "ai_transport", None)
    client, model = llm.client_from_settings(db, transport=transport)
    call = LlmCall(purpose="explain", model=model, ok=False)
    try:
        parsed, usage = client.chat_json(system, user)
    except ApiError:
        db.add(call)
        db.commit()
        raise
    finally:
        client.close()
    call.prompt_tokens = usage.prompt_tokens
    call.completion_tokens = usage.completion_tokens
    call.cost_estimate = llm.estimate_cost(model, usage)
    call.ok = True
    db.add(call)
    parsed["_model"] = model
    parsed["_created_at"] = utcnow().isoformat()
    enc.ai_explanation_json = json.dumps(parsed, ensure_ascii=False)
    db.commit()
    return {
        "explanation": parsed,
        "cached": False,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "cost_estimate": call.cost_estimate,
        },
    }


@router.get("/usage")
def usage(db: Session = Depends(get_db)) -> dict:
    totals = db.execute(
        select(
            func.count(LlmCall.id),
            func.coalesce(func.sum(LlmCall.prompt_tokens), 0),
            func.coalesce(func.sum(LlmCall.completion_tokens), 0),
            func.coalesce(func.sum(LlmCall.cost_estimate), 0.0),
        ).where(LlmCall.ok.is_(True))
    ).one()
    failed = db.scalar(select(func.count(LlmCall.id)).where(LlmCall.ok.is_(False))) or 0
    by_model = db.execute(
        select(
            LlmCall.model,
            func.count(LlmCall.id),
            func.coalesce(func.sum(LlmCall.cost_estimate), 0.0),
        )
        .where(LlmCall.ok.is_(True))
        .group_by(LlmCall.model)
    ).all()
    return {
        "calls": totals[0],
        "failed": failed,
        "prompt_tokens": int(totals[1]),
        "completion_tokens": int(totals[2]),
        "cost_estimate_usd": float(totals[3]),
        "by_model": [
            {"model": m, "calls": c, "cost_estimate_usd": float(cost)} for m, c, cost in by_model
        ],
    }


@router.get("/presets")
def presets() -> dict:
    return {"presets": llm.PRESETS, "prices_usd_per_1m": llm.PRICES}
