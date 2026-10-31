"""The Anthropic client against a mocked HTTP layer: success, retries and errors."""

import json

import httpx
import pytest

from app.services import ai
from app.services.ai import AIError, AnthropicClient, DesignFeedback, inline_schema

GOOD = {"summary": "Nice", "scores": {"brand_fit": 8, "trend": 7, "effortless": 9, "wearability": 8},
        "works": ["a"], "change": ["b"], "dna_takeaways": ["c"]}


def tool_reply(payload, tid="tu_1"):
    return {"content": [{"type": "tool_use", "id": tid, "name": "design_feedback", "input": payload}]}


def client_with(responses, seen):
    it = iter(responses)

    def handler(req: httpx.Request):
        seen.append(json.loads(req.content))
        status, body = next(it)
        return httpx.Response(status, json=body)

    return AnthropicClient("sk-test", "claude-test", transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(ai.time, "sleep", lambda _: None)


def test_schema_is_self_contained():
    s = json.dumps(inline_schema(DesignFeedback))
    assert "$ref" not in s and "$defs" not in s and "brand_fit" in s


def test_success_sends_forced_tool_and_image():
    seen = []
    c = client_with([(200, tool_reply(GOOD))], seen)
    out = c.structured(prompt="hi", schema=DesignFeedback, tool_name="design_feedback", images=[(b"img", "image/png")])
    assert out.scores.brand_fit == 8
    body = seen[0]
    assert body["tool_choice"] == {"type": "tool", "name": "design_feedback"}
    assert body["messages"][0]["content"][0]["type"] == "image"
    assert body["model"] == "claude-test"


def test_invalid_answer_is_retried_with_error_feedback():
    seen = []
    bad = dict(GOOD, scores={"brand_fit": 99, "trend": 7, "effortless": 9, "wearability": 8})
    c = client_with([(200, tool_reply(bad)), (200, tool_reply(GOOD, "tu_2"))], seen)
    out = c.structured(prompt="hi", schema=DesignFeedback, tool_name="design_feedback")
    assert out.summary == "Nice"
    retry_msgs = seen[1]["messages"]
    assert retry_msgs[-1]["content"][0]["type"] == "tool_result" and retry_msgs[-1]["content"][0]["is_error"]


def test_invalid_twice_raises():
    bad = {"summary": "x"}
    c = client_with([(200, tool_reply(bad)), (200, tool_reply(bad))], [])
    with pytest.raises(AIError):
        c.structured(prompt="hi", schema=DesignFeedback, tool_name="design_feedback")


def test_overloaded_then_ok():
    c = client_with([(529, {}), (429, {}), (200, tool_reply(GOOD))], [])
    assert c.structured(prompt="hi", schema=DesignFeedback, tool_name="design_feedback").summary == "Nice"


def test_bad_key_is_clear():
    c = client_with([(401, {"error": {}})], [])
    with pytest.raises(AIError) as e:
        c.structured(prompt="hi", schema=DesignFeedback, tool_name="design_feedback")
    assert "API key" in str(e.value) and e.value.status == 503


def test_gives_up_after_repeated_overload():
    c = client_with([(529, {})] * 4, [])
    with pytest.raises(AIError):
        c.structured(prompt="hi", schema=DesignFeedback, tool_name="design_feedback")
