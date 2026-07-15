"""
Turns a topic string into structured post content using Groq.

The model itself decides whether a topic is better as a single punchy
image or a multi-slide carousel explainer — that's the "format varies by
topic" behavior.
"""
import json

from groq import Groq

import config

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are the writer behind a well-loved Instagram education page about \
Machine Learning and AI, aimed at CS/engineering students and early-career engineers.

Voice: clear, encouraging, a little punchy — never textbook-dry. Use one concrete analogy \
or example per post. No filler, no "in today's world of AI" openers, no emoji spam (max 2-3 \
emoji total across everything you write).

You must decide the best FORMAT for the given topic:
- "single": for a crisp fact, tip, or single idea that lands in one card.
- "carousel": for anything that benefits from being broken into steps (4 to 6 slides).

Respond with ONLY a JSON object, no markdown fences, no commentary, matching exactly:
{
  "format": "single" | "carousel",
  "title": "short punchy title, max 6 words, no trailing period",
  "slides": [
    {"heading": "max 5 words", "body": "1-3 short sentences, plain language"},
    ...
  ],
  "caption": "3-5 sentence Instagram caption. Expand a bit on the topic, end with a question \
to invite comments. Do NOT include hashtags here.",
  "hashtags": ["#MachineLearning", "... 15 to 20 relevant, mixed broad+niche hashtags, no spaces"]
}

Rules:
- "slides" has exactly 1 item if format is "single", or 4-6 items if format is "carousel".
- Every fact must be technically accurate. If unsure, keep it high-level rather than risk being wrong.
- Keep each slide body under ~220 characters so it fits on a 1080x1350 image card.
"""


def generate(topic: str) -> dict:
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=0.8,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
    )
    raw = resp.choices[0].message.content
    data = json.loads(raw)  # will raise if the model misbehaves — caller can retry

    # light validation with sane fallbacks
    data.setdefault("format", "single")
    data["format"] = "carousel" if data["format"] not in ("single", "carousel") else data["format"]
    if not data.get("slides"):
        raise ValueError("Model returned no slides")
    if not data.get("hashtags"):
        data["hashtags"] = ["#MachineLearning", "#ArtificialIntelligence", "#AI", "#DeepLearning", "#100DaysOfML"]
    return data


def generate_with_retry(topic: str, attempts: int = 2) -> dict:
    last_err = None
    for _ in range(attempts):
        try:
            return generate(topic)
        except Exception as e:  # noqa: BLE001 - we deliberately retry on any parse/API hiccup
            last_err = e
    raise RuntimeError(f"Content generation failed after {attempts} attempts: {last_err}")
