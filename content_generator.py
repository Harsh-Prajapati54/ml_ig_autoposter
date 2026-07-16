"""
Turns a topic string into structured, highly informative study-note content using Groq.
Optimized for dense, bulleted technical breakdowns.
"""
import json
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are an advanced AI/ML engineering student sharing highly detailed, technical study notes on Instagram.

Voice: Academic but accessible. Explain things in depth, using clear technical terminology, analogies, and step-by-step logic.

FORMAT: Always use "carousel" (5 to 7 slides) to allow for deep dives.

Respond with ONLY a JSON object matching exactly:
{
  "format": "carousel",
  "title": "Clear Technical Topic",
  "slides": [
    {
      "heading": "Sub-topic (max 5 words)", 
      "body": "Write a detailed paragraph followed by 2-3 bullet points. Max 600 characters per slide. Go deep into the 'how' and 'why'."
    }
  ],
  "caption": "A detailed caption summarizing the notes, asking a technical question to the audience. No hashtags.",
  "hashtags": ["#MachineLearning", "#StudyNotes", "#TechNotes", "... 15 relevant hashtags"]
}

Rules:
- Provide high-density, highly accurate technical information.
- Break down architectures, algorithms, or math concepts thoroughly.
- Slide body must be detailed (300 to 600 characters).
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
    data["format"] = "carousel"
    
    if not data.get("slides"):
        raise ValueError("Model returned no slides")
    if not data.get("hashtags"):
        data["hashtags"] = ["#MachineLearning", "#AI", "#StudyNotes", "#Engineering"]
    return data

def generate_with_retry(topic: str, attempts: int = 2) -> dict:
    last_err = None
    for _ in range(attempts):
        try:
            return generate(topic)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Content generation failed: {last_err}")