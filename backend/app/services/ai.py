"""Claude integration.

Every AI feature asks Claude to call one tool whose input schema is a Pydantic
model, so answers always arrive as structured, validated data. A malformed
answer is retried once; transient API errors (429, 5xx, timeouts) back off and
retry up to three times.

The client is an interface so tests (and local work without a key) use a fake.
"""

from __future__ import annotations

import base64
import copy
import logging
import time
from typing import Literal, Protocol, TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIError(Exception):
    """An AI call failed in a way the user should hear about."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------- output shapes

class Colour(BaseModel):
    name: str
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class TrendIdea(BaseModel):
    name: str = Field(description="Short evocative name for the direction")
    fit: int = Field(ge=0, le=100, description="Fit with this brand's DNA and customer, 0-100")
    lifespan: Literal["micro", "season", "long"]
    why: str = Field(description="Two sentences on what's driving it, citing the founder's signals by name")
    our_take: str = Field(description="How this brand would translate it into hoodies, tees, sweatshirts, sweatpants")
    colours: list[Colour] = Field(min_length=2, max_length=5)
    search_terms: list[str] = Field(min_length=3, max_length=6, description="Specific Pinterest/TikTok search phrases")
    avoid: str = Field(description="The try-hard version to stay away from")


class TrendScout(BaseModel):
    trends: list[TrendIdea] = Field(min_length=3, max_length=5)
    summary: str = Field(description="One sentence on which direction to pick and why")


class PieceIdea(BaseModel):
    category: Literal["hoodie", "t-shirt", "sweatshirt", "sweatpants"]
    name: str
    color: str
    fit: str
    fabric: str
    gsm: int = Field(ge=120, le=600)


class LookIdea(BaseModel):
    name: str
    pieces: list[PieceIdea] = Field(min_length=2, max_length=3)
    signature_detail: str = Field(description="The one quiet detail that makes this look ownable")


class StoreMood(BaseModel):
    lighting: str
    scent: str
    sound: str
    display: str
    ritual: str = Field(description="A small moment every customer gets")


class DropConcept(BaseModel):
    name: str
    story: str
    palette: list[Colour] = Field(min_length=3, max_length=6)
    looks: list[LookIdea] = Field(min_length=4, max_length=4)
    store: StoreMood
    moodboard: list[str] = Field(min_length=4, max_length=8)
    avoid: list[str] = Field(min_length=1, max_length=4)


class Scores(BaseModel):
    brand_fit: int = Field(ge=1, le=10)
    trend: int = Field(ge=1, le=10)
    effortless: int = Field(ge=1, le=10)
    wearability: int = Field(ge=1, le=10)


class DesignFeedback(BaseModel):
    summary: str = Field(description="One-sentence verdict")
    scores: Scores
    works: list[str] = Field(min_length=1, max_length=5)
    change: list[str] = Field(min_length=1, max_length=5, description="Specific, actionable changes")
    dna_takeaways: list[str] = Field(
        min_length=1, max_length=3, description="Reusable brand rules this design teaches, written as instructions"
    )


# ------------------------------------------------------------------- clients

class AIClient(Protocol):
    def structured(
        self, *, prompt: str, schema: type[T], tool_name: str, images: list[tuple[bytes, str]] | None = None
    ) -> T: ...


def inline_schema(model: type[BaseModel]) -> dict:
    """Pydantic emits $defs/$ref; inline them so the tool schema is self-contained."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


class AnthropicClient:
    url = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str, timeout: float = 180.0, transport: httpx.BaseTransport | None = None):
        self.model = model
        self.http = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        )

    def _post(self, body: dict) -> dict:
        delay = 2.0
        for attempt in range(4):
            try:
                r = self.http.post(self.url, json=body)
            except httpx.TimeoutException:
                if attempt == 3:
                    raise AIError("Claude took too long to answer. Try again.", 504)
            else:
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (401, 403):
                    raise AIError("The Anthropic API key was rejected. Check ANTHROPIC_API_KEY.", 503)
                if r.status_code == 400:
                    log.error("Anthropic 400: %s", r.text[:500])
                    raise AIError("Claude couldn't process that request.", 502)
                if r.status_code not in (429, 500, 502, 503, 529) or attempt == 3:
                    log.error("Anthropic %s: %s", r.status_code, r.text[:500])
                    raise AIError("Claude is busy right now. Try again in a minute.", 503)
            time.sleep(delay)
            delay *= 2
        raise AIError("Claude is unavailable right now.", 503)  # pragma: no cover

    def structured(self, *, prompt, schema, tool_name, images=None):
        content: list[dict] = []
        for data, media_type in images or []:
            content.append(
                {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.b64encode(data).decode()}}
            )
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        tool = {"name": tool_name, "description": f"Return the {tool_name.replace('_', ' ')}.",
                "input_schema": inline_schema(schema)}

        for attempt in range(2):
            data = self._post({
                "model": self.model,
                "max_tokens": 8000,
                "tools": [tool],
                "tool_choice": {"type": "tool", "name": tool_name},
                "messages": messages,
            })
            block = next((b for b in data.get("content", []) if b.get("type") == "tool_use"), None)
            if block is None:
                raise AIError("Claude didn't return a usable answer. Try again.")
            try:
                return schema.model_validate(block["input"])
            except ValidationError as e:
                if attempt == 1:
                    log.error("AI output failed validation twice: %s", e)
                    raise AIError("Claude's answer didn't match the expected format. Try again.")
                messages = messages + [
                    {"role": "assistant", "content": data["content"]},
                    {"role": "user", "content": [{
                        "type": "tool_result", "tool_use_id": block["id"], "is_error": True,
                        "content": f"Invalid: {e.errors(include_url=False)[:5]}. Call the tool again with valid input.",
                    }]},
                ]
        raise AIError("Claude's answer didn't match the expected format.")  # pragma: no cover


class DisabledClient:
    def structured(self, **_):
        raise AIError("AI isn't set up yet. Add ANTHROPIC_API_KEY to the backend's environment.", 503)


# ------------------------------------------------------------------- prompts

BRIEF = (
    "The business model: only 4 complete outfits per drop, a new drop roughly every two months. "
    "Silhouettes are hoodies, t-shirts, sweatshirts and sweatpants. Customers walk in already knowing "
    "which look they want, and the store visit is an experience. The feel is premium and effortless, "
    "like Fear of God Essentials: never loud, never trying too hard, never Gucci-level luxury."
)


def scout_prompt(context: str, signals: str, launch_month: str, hint: str) -> str:
    return f"""You are the trend strategist for a small premium basics brand.

{BRIEF}

{context}

TREND SIGNALS THE FOUNDER COLLECTED (newest first):
{signals or "(none yet)"}

The next drop launches {launch_month}. {"Founder's note: " + hint if hint else ""}

Rank the 3-5 strongest trend directions for this drop. Weigh her signals heavily, use your knowledge of
fashion cycles and timing (what will still feel fresh at launch, not what peaked already), and judge fit
against the brand DNA. Each direction must translate into the four silhouettes without looking costume-like.
Prefer directions the brand can own quietly over loud fads. Order by fit, best first."""


def drop_prompt(context: str, trend: str, launch_month: str, direction: str) -> str:
    return f"""You are the creative director of a small premium basics brand.

{BRIEF}

{context}

Design the drop around the trend "{trend}", launching {launch_month}.
{"Founder's direction: " + direction if direction else ""}

Rules:
- Exactly 4 complete outfits, each 2-3 pieces from: hoodie, t-shirt, sweatshirt, sweatpants.
- Luxury comes from fabric weight, fit, colour and ONE quiet signature detail per look. No big logos.
- Every look is something a customer would come in already wanting; together they tell one story.
- Respect every brand DNA rule. Learn from past drops' sell-through: lean into what sold.
- Realistic specs (e.g. 420 gsm brushed-back fleece, 240 gsm compact cotton jersey).
- Store mood should be achievable for a small shop, not a flagship budget."""


def review_prompt(context: str, title: str, note: str, drop_summary: str) -> str:
    return f"""You are a senior design director giving honest, specific feedback to the founder of a small
premium basics brand. The image is her design: a sketch, technical flat, or photo.

{BRIEF}

{context}

{drop_summary}
Design: {title}
What she's going for: {note or "(not stated)"}

Judge it against the brand DNA, the drop's trend, and the bar of "premium, effortless, never trying too hard".
Be direct and practical: name exactly what to change (proportion, fabric weight, colour, placement, trims).
Then extract 1-3 reusable brand DNA rules this design teaches, phrased as instructions for future drops."""
