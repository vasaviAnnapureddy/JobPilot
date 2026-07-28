# -*- coding: utf-8 -*-
"""
EMBEDDINGS — turns text into a 768-number vector that captures its MEANING.

This is the engine behind RAG. Two pieces of text with similar meaning get
similar vectors, even if they use different words ("built ML models" vs
"developed predictive algorithms"). We use Google's text-embedding-004,
which outputs 768 dimensions — matching the vector(768) column in the
database schema.

Cosine similarity (below) measures how close two vectors point: 1.0 = same
meaning, 0 = unrelated. That's how we find which parts of the resume are
most relevant to a given job description.
"""

import math
from core import config


def embed(text, task="RETRIEVAL_DOCUMENT"):
    """
    Return a 768-dim embedding for the text, or None if it fails.
    task = 'RETRIEVAL_DOCUMENT' for stored text (resume/JD),
           'RETRIEVAL_QUERY' for the thing you're searching with.
    """
    text = (text or "").strip()
    if not text:
        return None

    for api_key in config.GEMINI_KEYS:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            resp = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text[:8000],
                config=types.EmbedContentConfig(
                    task_type=task,
                    output_dimensionality=768,   # matches vector(768) in schema
                ),
            )
            return list(resp.embeddings[0].values)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "503" in err:
                continue          # try next key
            # unknown error — stop trying, return None so caller can fall back
            return None
    return None


def cosine_similarity(v1, v2):
    """How aligned two vectors are: 1.0 = identical meaning, 0 = unrelated."""
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1  = math.sqrt(sum(a * a for a in v1))
    n2  = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)
