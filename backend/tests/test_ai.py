import json

import httpx
import pytest

from kotoba.services.ai import keys, pricing


def _completion(content: str, prompt=120, completion=80, hit=20):
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "prompt_cache_hit_tokens": hit,
        },
    }


def _setup(client):
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    for text in ["おはよう。", "今日は暇？", "うん、暇だよ。", "じゃあ出かけよう。"]:
        client.post("/api/lines", json={"session_id": ses["id"], "text": text})
    text = "しょうがないなぁ…今日は俺が奢ってやるよ。"
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": text}).json()["line"]
    client.post("/api/lines", json={"session_id": ses["id"], "text": "え、本当に？"})  # later line
    enc = client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "奢る",
            "reading": "おごる",
            "surface": "奢っ",
            "span_start": text.index("奢っ"),
            "span_end": text.index("奢っ") + 2,
            "sense": {"gloss_zh": "请客"},
        },
    ).json()
    return enc["encounter"]["id"]


@pytest.fixture()
def ai_client(client, monkeypatch):
    monkeypatch.setenv("KOTOBA_AI_KEY", "sk-test")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        if seen.get("mode") == "bad":
            return httpx.Response(200, json=_completion("not json"))
        if seen.get("mode") == "http500":
            return httpx.Response(500, text="boom")
        answer = {
            "meaning_here": "我来请客",
            "form": "奢る 的て形+やる",
            "tone": "亲近、随意",
            "needs_context": None,
            "daily_usable": "朋友之间可以",
            "trap_for_zh": None,
            "confidence": 0.9,
        }
        return httpx.Response(
            200, json=_completion("```json\n" + json.dumps(answer, ensure_ascii=False) + "\n```")
        )

    client.app.state.ai_transport = httpx.MockTransport(handler)
    client.seen = seen
    return client


def test_explain_sends_only_prior_context_and_caches(ai_client):
    enc_id = _setup(ai_client)
    r = ai_client.post("/api/ai/explain", json={"encounter_id": enc_id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cached"] is False and body["explanation"]["meaning_here"] == "我来请客"
    assert body["explanation"]["_model"] == "deepseek-flash"
    assert body["usage"]["cost_estimate"] > 0
    seen = ai_client.seen
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == "deepseek-flash"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    user_msg = seen["body"]["messages"][1]["content"]
    assert "奢っ" in user_msg and "请客" in user_msg
    assert (
        "今日は暇？" in user_msg
        and "うん、暇だよ。" in user_msg
        and "じゃあ出かけよう。" in user_msg
    )
    assert "おはよう" not in user_msg  # only the last 3 prior lines
    assert "え、本当に？" not in user_msg  # never lines after the target

    cached = ai_client.post("/api/ai/explain", json={"encounter_id": enc_id}).json()
    assert cached["cached"] is True
    usage = ai_client.get("/api/ai/usage").json()
    assert usage["calls"] == 1 and usage["prompt_tokens"] == 120 and usage["cost_estimate_usd"] > 0
    term = ai_client.get("/api/terms", params={"q": "奢"}).json()[0]
    detail = ai_client.get(f"/api/terms/{term['id']}").json()
    assert detail["encounters"][0]["ai_explanation"]["tone"] == "亲近、随意"


def test_explain_failures_are_logged_and_do_not_break_encounter(ai_client):
    enc_id = _setup(ai_client)
    ai_client.seen["mode"] = "bad"
    r = ai_client.post("/api/ai/explain", json={"encounter_id": enc_id})
    assert r.status_code == 502 and r.json()["error"]["code"] == "ai_failed"
    ai_client.seen["mode"] = "http500"
    assert ai_client.post("/api/ai/explain", json={"encounter_id": enc_id}).status_code == 502
    usage = ai_client.get("/api/ai/usage").json()
    assert usage["calls"] == 0 and usage["failed"] == 2
    term = ai_client.get("/api/terms", params={"q": "奢"}).json()[0]
    assert (
        ai_client.get(f"/api/terms/{term['id']}").json()["encounters"][0]["ai_explanation"] is None
    )


def test_explain_requires_key(client, monkeypatch):
    monkeypatch.delenv("KOTOBA_AI_KEY", raising=False)
    monkeypatch.setattr(keys, "get_api_key", lambda provider: (None, "none"))
    enc_id = _setup(client)
    r = client.post("/api/ai/explain", json={"encounter_id": enc_id})
    assert r.status_code == 400 and r.json()["error"]["code"] == "ai_not_configured"
    status = client.get("/api/settings/ai-key").json()
    assert status == {"provider": "deepseek", "configured": False, "source": "none"}


def test_cost_estimate_uses_cache_hits():
    usage = pricing.Usage(prompt_tokens=1_000_000, completion_tokens=0, cache_hit_tokens=1_000_000)
    assert pricing.estimate_cost("deepseek-flash", usage) == pytest.approx(0.006)
    usage = pricing.Usage(prompt_tokens=1_000_000, completion_tokens=1_000_000, cache_hit_tokens=0)
    assert pricing.estimate_cost("deepseek-flash", usage) == pytest.approx(1.50)


def test_api_key_sources_are_tried_in_order(monkeypatch, tmp_path):
    """env var → .env → keyring. The keyring is the intended home; the other two
    exist for headless setups, so they must not be silently ignored."""
    from kotoba.core.config import get_settings
    from kotoba.services.ai import keys

    monkeypatch.setattr(keys, "KEYRING_SERVICE", "kotoba-studio-test")
    monkeypatch.delenv(keys.ENV_KEY, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text("KOTOBA_AI_KEY=from-env-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    assert keys.get_api_key("deepseek") == ("from-env-file", "env file")

    monkeypatch.setenv(keys.ENV_KEY, "from-real-env")
    get_settings.cache_clear()
    assert keys.get_api_key("deepseek") == ("from-real-env", "env")

    monkeypatch.delenv(keys.ENV_KEY)
    env_file.unlink()
    get_settings.cache_clear()
    assert keys.get_api_key("deepseek")[1] in ("keyring", "none")
    get_settings.cache_clear()
