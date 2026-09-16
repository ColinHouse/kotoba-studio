import sys
import time
import types

import fsrs

from kotoba.models import ReviewLog, utcnow
from kotoba.services import settings_store
from kotoba.services.review import optimize, scheduler

DEFAULT_PARAMETERS = list(scheduler.Scheduler().parameters)
NEW_PARAMETERS = [p * 1.05 for p in DEFAULT_PARAMETERS]  # valid, unlike a flat list


class FakeOptimizer:
    """Stands in for fsrs.Optimizer, which needs the [optimizer] extra (torch)."""

    def __init__(self, review_logs):
        self.review_logs = review_logs

    def compute_optimal_parameters(self):
        return NEW_PARAMETERS

    def compute_optimal_retention(self, parameters):
        assert parameters == NEW_PARAMETERS
        return 0.88


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def seed_card(client) -> int:
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": "猫"}).json()["line"]
    enc = client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "猫",
            "reading": "ねこ",
            "surface": "猫",
            "card_types": ["reading"],
        },
    ).json()
    return enc["cards"][0]["id"]


def seed_logs(db, card_id: int, scheduled: int, quiz: int = 0) -> None:
    now = utcnow()
    db.add_all(
        [
            ReviewLog(card_id=card_id, rating=3, mode="scheduled", reviewed_at=now)
            for _ in range(scheduled)
        ]
        + [
            ReviewLog(card_id=card_id, rating=3, mode="session_quiz", reviewed_at=now)
            for _ in range(quiz)
        ]
    )
    db.commit()


def test_optimize_rejects_too_few_reviews(client):
    r = client.post("/api/reviews/optimize")
    assert r.status_code == 400
    error = r.json()["error"]
    assert error["code"] == "not_enough_reviews"
    assert "400" in error["message"] and "还差" in error["message"]


def test_optimize_runs_in_background_and_reports_the_result(client, db, monkeypatch):
    card_id = seed_card(client)
    seed_logs(db, card_id, scheduled=400, quiz=7)
    monkeypatch.setattr(fsrs, "Optimizer", FakeOptimizer)
    monkeypatch.setitem(sys.modules, "torch", types.ModuleType("torch"))

    started = client.post("/api/reviews/optimize")
    assert started.status_code == 200
    assert started.json()["state"] in ("running", "done")

    assert wait_for(
        lambda: client.get("/api/reviews/optimize").json()["state"] == "done",
        timeout=10,
    )
    result = client.get("/api/reviews/optimize").json()["result"]
    assert result["review_count"] == 400  # session quizzes never feed the optimizer
    assert result["old_parameters"] is None
    assert result["new_parameters"] == NEW_PARAMETERS
    assert result["optimal_retention"] == 0.88


def test_optimize_reports_the_missing_extra(client, db, monkeypatch):
    card_id = seed_card(client)
    seed_logs(db, card_id, scheduled=400)
    monkeypatch.setitem(sys.modules, "torch", None)  # as if kotoba[optimizer] were absent

    r = client.post("/api/reviews/optimize")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "optimizer_unavailable"
    assert "optimizer" in r.json()["error"]["message"]


def test_scheduler_reads_parameters_from_settings(client, db):
    assert scheduler.scheduler(db).parameters == tuple(DEFAULT_PARAMETERS)

    settings_store.set_value(db, "fsrs_parameters", NEW_PARAMETERS)
    db.commit()
    assert scheduler.scheduler(db).parameters == tuple(NEW_PARAMETERS)


def test_apply_and_restore_parameters_via_settings(client):
    r = client.put(
        "/api/settings",
        json={"fsrs_parameters": NEW_PARAMETERS, "fsrs_parameters_previous": None},
    )
    assert r.status_code == 200
    settings = r.json()
    assert settings["fsrs_parameters"] == NEW_PARAMETERS

    r = client.put(
        "/api/settings",
        json={"fsrs_parameters": None, "fsrs_parameters_previous": NEW_PARAMETERS},
    )
    assert r.json()["fsrs_parameters"] is None
    assert r.json()["fsrs_parameters_previous"] == NEW_PARAMETERS


def test_invalid_parameters_are_rejected(client):
    r = client.put("/api/settings", json={"fsrs_parameters": [1, 2]})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_value"


def test_min_reviews_constant_is_four_hundred():
    assert optimize.MIN_REVIEWS == 400
