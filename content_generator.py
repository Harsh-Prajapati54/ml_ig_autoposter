"""
Turns a topic string into structured post content using Groq.
Now includes Mermaid.js syntax generation for technical diagrams.
"""
import json
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are the writer behind a highly technical Instagram education page about \
Machine Learning and AI, aimed at CS students and engineers.

Voice: clear, encouraging, punchy. No filler, no emoji spam (max 2 total).

You must decide the best FORMAT for the topic ("single" or "carousel").
CRITICAL: If a slide explains an architecture, pipeline, or relationship, provide valid Mermaid.js flowchart syntax in the "diagram" field. Use a top-down (graph TD) or left-right (graph LR) layout. Keep it simple (3-6 nodes max). If no diagram is needed, set "diagram" to null.

Respond with ONLY a JSON object matching exactly:
{
  "format": "single" | "carousel",
  "title": "short punchy title, max 6 words",
  "slides": [
    {
      "heading": "max 5 words", 
      "body": "1-3 short sentences, plain language",
      "diagram": "graph TD;\n A[Raw Data] --> B[Processing];\n B --> C[Model];" 
    }
  ],
  "caption": "3-5 sentence Instagram caption. End with a question. No hashtags here.",
  "hashtags": ["#MachineLearning", "... 15 relevant hashtags"]
}

Rules:
- "slides" has exactly 1 item if format is "single", or 4-6 if "carousel".
- Mermaid syntax must be flawless and simple.
- Slide body under ~200 characters.
"""

def generate(topic: str) -> dict:
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=0.7,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Topic: {topic}"},
        ],
    )
    raw = resp.choices[0].message.content
    data = json.loads(raw)

    data.setdefault("format", "single")
    data["format"] = "carousel" if data["format"] not in ("single", "carousel") else data["format"]
    if not data.get("slides"):
        raise ValueError("Model returned no slides")
    if not data.get("hashtags"):
        data["hashtags"] = ["#MachineLearning", "#AI", "#DeepLearning", "#ComputerScience"]
    return data

def generate_with_retry(topic: str, attempts: int = 2) -> dict:
    last_err = None
    for _ in range(attempts):
        try:
            return generate(topic)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Content generation failed: {last_err}")