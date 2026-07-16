"""
Turns a topic string into structured study-note content using Groq.
Requests clean bullet points and transparent Mermaid diagrams.
"""
import json
from groq import Groq
import config

client = Groq(api_key=config.GROQ_API_KEY)

SYSTEM_PROMPT = """You are an advanced AI/ML engineering student sharing highly detailed study notes.

Voice: Academic, clear, and structured. 

FORMAT: Always use "carousel" (4 to 6 slides).
CRITICAL: Use standard ASCII hyphens (-) for bullet points. Do NOT use special unicode dots or em-dashes. Use \n for line breaks.
DIAGRAMS: If a slide explains an architecture, process, or comparison, provide valid Mermaid.js syntax in the "diagram" field (flowcharts, graphs, or tables). If no diagram is needed, set it to null. Keep diagrams simple (max 5-6 nodes).

Respond with ONLY a JSON object matching exactly:
{
  "format": "carousel",
  "title": "Clear Technical Topic",
  "slides": [
    {
      "heading": "Sub-topic (max 5 words)", 
      "body": "Paragraph 1 explaining the concept.\n\n- Bullet point 1 detailing how it works.\n- Bullet point 2 with an example.",
      "diagram": "graph TD;\n A[Data] --> B[Model];"
    }
  ],
  "caption": "A detailed caption summarizing the notes. Ask a question. No hashtags.",
  "hashtags": ["#MachineLearning", "#StudyNotes", "... 15 relevant hashtags"]
}
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