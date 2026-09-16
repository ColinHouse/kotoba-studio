"""Personalize FSRS parameters with the user's own scheduled reviews.

py-fsrs ships an Optimizer that fits the parameters to one person's history,
but it pulls torch, so it lives behind the `optimizer` extra and is imported
lazily. Fitting takes minutes, so it runs in a background thread and the
result is never applied automatically. Session quizzes are excluded: they are
not evidence of long-term retention (invariant 1).
"""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import ReviewLog
from kotoba.services import settings_store

MIN_REVIEWS = 400


def load_optimizer():
    """Return fsrs.Optimizer, or a readable ApiError when the extra is absent.

    fsrs exposes a stub Optimizer whose constructor raises, so probe for the
    extra's torch import first and keep the failure lazy (invariant 7).
    """
    try:
        importlib.import_module("torch")
        from fsrs import Optimizer
    except ImportError as exc:
        raise ApiError(
            "optimizer_unavailable",
            "未安装 FSRS 优化器：安装 kotoba[optimizer] 后可用（会一并安装 torch）",
            503,
        ) from exc
    return Optimizer


def count_scheduled(db: Session) -> int:
    return db.scalar(select(func.count(ReviewLog.id)).where(ReviewLog.mode == "scheduled")) or 0


def review_logs(db: Session) -> list:
    """All scheduled review logs in chronological order, as py-fsrs objects."""
    from fsrs import Rating
    from fsrs import ReviewLog as FsrsReviewLog

    rows = db.scalars(
        select(ReviewLog)
        .where(ReviewLog.mode == "scheduled")
        .order_by(ReviewLog.reviewed_at, ReviewLog.id)
    ).all()
    return [
        FsrsReviewLog(
            card_id=row.card_id,
            rating=Rating(row.rating),
            review_datetime=row.reviewed_at,
            review_duration=int(row.duration_ms / 1000) if row.duration_ms else None,
        )
        for row in rows
    ]


class OptimizeJob:
    """Background parameter fitting with observable state."""

    def __init__(self) -> None:
        self.state = "idle"
        self.message = ""
        self.result: dict | None = None
        self._thread: threading.Thread | None = None

    def snapshot(self) -> dict:
        return {"state": self.state, "message": self.message, "result": self.result}

    def start(self, session_factory: Callable[[], Session]) -> bool:
        if self._thread and self._thread.is_alive():
            return False

        def run() -> None:
            db = session_factory()
            try:
                self.state, self.message = "running", "正在读取复习记录…"
                logs = review_logs(db)
                optimizer_class = load_optimizer()
                old_parameters = settings_store.get(db, "fsrs_parameters")
                self.message = "正在优化参数（可能要几分钟）…"
                optimizer = optimizer_class(logs)
                new_parameters = [float(p) for p in optimizer.compute_optimal_parameters()]
                retention = optimizer.compute_optimal_retention(new_parameters)
                self.result = {
                    "review_count": len(logs),
                    "old_parameters": old_parameters,
                    "new_parameters": new_parameters,
                    "optimal_retention": float(retention),
                }
                self.state, self.message = "done", "优化完成"
            except ApiError as exc:
                self.state, self.message = "error", exc.message
            except Exception as exc:  # noqa: BLE001
                self.state, self.message = "error", str(exc)
            finally:
                db.close()

        self._thread = threading.Thread(target=run, name="fsrs-optimize", daemon=True)
        self._thread.start()
        return True


optimize_job = OptimizeJob()
