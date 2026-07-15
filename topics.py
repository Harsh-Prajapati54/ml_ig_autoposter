"""
Topic pool + rotation so the page doesn't repeat itself constantly.

State (which topics were recently used) is stored as data/used_topics.json
and persisted back to GitHub via the Contents API after every run, so it
survives GitHub Actions' throwaway runners.
"""
import json
import os
import random

import config
import github_host

TOPICS = [
    # Core ML
    "Supervised vs unsupervised learning",
    "Bias-variance tradeoff",
    "Overfitting and regularization",
    "Gradient descent, intuitively",
    "Train/validation/test splits",
    "Precision vs recall",
    "Feature engineering basics",
    "Cross-validation explained",
    "Confusion matrices",
    "L1 vs L2 regularization",
    # Deep Learning
    "How a neural network actually learns",
    "Backpropagation without the scary math",
    "What activation functions do",
    "Batch normalization, intuitively",
    "CNNs: how machines 'see' images",
    "Why deep learning needs so much data",
    "Vanishing gradients explained",
    "Dropout: teaching a network to not memorize",
    "Transfer learning in plain English",
    "What a loss function really measures",
    # NLP / LLMs
    "How transformers work (no equations)",
    "What is 'attention' in attention is all you need",
    "Tokens vs words: how LLMs read text",
    "What is RAG and why everyone's building it",
    "Embeddings: turning meaning into numbers",
    "Fine-tuning vs prompting vs RAG",
    "Why LLMs hallucinate",
    "What a context window actually is",
    "LoRA / QLoRA explained simply",
    "How ChatGPT-style models are trained (RLHF)",
    # Computer Vision
    "Object detection vs image classification",
    "What Grad-CAM shows you about a model",
    "How self-driving cars 'see' the road",
    # MLOps / Practical
    "Why your model works in notebook, fails in prod",
    "What MLOps actually means",
    "Data leakage: the silent model killer",
    "Vector databases explained",
    "What RAGAS/eval metrics tell you about a RAG pipeline",
    "Why reranking improves retrieval",
    "BM25 vs dense retrieval vs hybrid search",
    # AI concepts & career
    "AI vs ML vs Deep Learning vs GenAI",
    "What a Kaggle competition teaches you that a course doesn't",
    "Reading a research paper as a student: where to start",
    "Building your first real ML project: what actually matters",
    "The math you actually need for ML (and what you don't)",
]

STATE_PATH = os.path.join(config.DATA_DIR, "used_topics.json")
REMOTE_STATE_PATH = "data/used_topics.json"


def _load_state() -> list:
    """Pull the 'recently used' list from GitHub (falls back to empty)."""
    content = github_host.download_json(REMOTE_STATE_PATH)
    if content is not None:
        return content.get("recent", [])
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f).get("recent", [])
    return []


def _save_state(recent: list) -> None:
    payload = {"recent": recent}
    with open(STATE_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    github_host.upload_json(REMOTE_STATE_PATH, payload, message="chore: update used_topics.json")


def pick_topic() -> str:
    """Pick a topic, avoiding the last N used (wraps around once exhausted)."""
    recent = _load_state()
    avoid = set(recent[-15:])  # don't repeat the last ~15 posts' topics
    candidates = [t for t in TOPICS if t not in avoid] or TOPICS
    topic = random.choice(candidates)
    recent.append(topic)
    _save_state(recent)
    return topic
