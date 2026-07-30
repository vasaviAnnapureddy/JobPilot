# -*- coding: utf-8 -*-
"""
RAG — Retrieval-Augmented Generation for job matching.

The idea:
  1. Split my resume into small "chunks" (each project, skill block, internship).
  2. Embed each chunk into a meaning-vector once (cached to disk).
  3. For a given job description, embed it, then RETRIEVE the resume chunks
     whose meaning is closest (cosine similarity).
  4. Those retrieved chunks are handed to the Judge as EVIDENCE, so grading
     is grounded in my actual background — not generic guessing.

This is real retrieval: the LLM only sees the parts of my resume that
actually relate to the job.
"""

import json
import re
from pathlib import Path

from core import config, embeddings

# Each resume PROFILE gets its own file + its own cached index.
#   profile "master"       -> cv_master.md       -> resume_chunks.json
#   profile "data_science" -> cv_data_science.md -> resume_chunks_data_science.json
# This is what lets a Data Science resume match data-science jobs and an
# AI resume match AI jobs — separately.

def _resume_path(profile):
    if profile == "master":
        return config.RESUMES_DIR / "cv_master.md"
    return config.RESUMES_DIR / f"cv_{profile}.md"


def _cache_path(profile):
    if profile == "master":
        return config.RESUMES_DIR / "resume_chunks.json"
    return config.RESUMES_DIR / f"resume_chunks_{profile}.json"


def _split_resume(md_text):
    """Split resume markdown into meaningful chunks (by heading/blank lines)."""
    raw = re.split(r"\n(?=#{1,3}\s)|\n\s*\n", md_text)
    chunks = []
    for block in raw:
        block = block.strip()
        if len(block) >= 40:          # skip tiny fragments
            chunks.append(block[:1000])
    return chunks


def build_index(profile="master", force=False):
    """Embed a profile's resume chunks and cache to disk. Returns chunk count."""
    cv = _resume_path(profile)
    if not cv.exists():
        # fall back to master resume if this profile has none yet
        cv = _resume_path("master")
        if not cv.exists():
            return 0
    cache = _cache_path(profile)

    if cache.exists() and not force:
        return len(json.loads(cache.read_text(encoding="utf-8")))

    chunks = _split_resume(cv.read_text(encoding="utf-8"))
    indexed = []
    for ch in chunks:
        vec = embeddings.embed(ch, task="RETRIEVAL_DOCUMENT")
        if vec:
            indexed.append({"text": ch, "vector": vec})

    cache.write_text(json.dumps(indexed), encoding="utf-8")
    return len(indexed)


def retrieve(job_text, profile="master", top_k=3):
    """Return the top_k resume chunks (from this profile's resume) closest in meaning."""
    cache = _cache_path(profile)
    if not cache.exists():
        build_index(profile)
    if not cache.exists():
        return []

    index = json.loads(cache.read_text(encoding="utf-8"))
    q_vec = embeddings.embed(job_text, task="RETRIEVAL_QUERY")
    if not q_vec:
        return []

    scored = [
        (embeddings.cosine_similarity(q_vec, item["vector"]), item["text"])
        for item in index
    ]
    scored.sort(reverse=True, key=lambda x: x[0])
    return [text for _score, text in scored[:top_k]]
