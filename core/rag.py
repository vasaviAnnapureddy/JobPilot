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

CHUNK_CACHE = config.RESUMES_DIR / "resume_chunks.json"


def _split_resume(md_text):
    """Split resume markdown into meaningful chunks (by heading/blank lines)."""
    # Split on markdown headings or double newlines
    raw = re.split(r"\n(?=#{1,3}\s)|\n\s*\n", md_text)
    chunks = []
    for block in raw:
        block = block.strip()
        if len(block) >= 40:          # skip tiny fragments
            chunks.append(block[:1000])
    return chunks


def build_index(force=False):
    """
    Embed every resume chunk and cache to disk. Run once (or after the
    resume changes). Returns the number of chunks indexed.
    """
    cv = config.RESUMES_DIR / "cv_master.md"
    if not cv.exists():
        return 0

    if CHUNK_CACHE.exists() and not force:
        return len(json.loads(CHUNK_CACHE.read_text(encoding="utf-8")))

    chunks = _split_resume(cv.read_text(encoding="utf-8"))
    indexed = []
    for ch in chunks:
        vec = embeddings.embed(ch, task="RETRIEVAL_DOCUMENT")
        if vec:
            indexed.append({"text": ch, "vector": vec})

    CHUNK_CACHE.write_text(json.dumps(indexed), encoding="utf-8")
    return len(indexed)


def retrieve(job_text, top_k=3):
    """
    Given a job description, return the top_k most relevant resume chunks
    (as plain text) to use as grading evidence. Falls back to [] if the
    index or embeddings are unavailable.
    """
    if not CHUNK_CACHE.exists():
        build_index()
    if not CHUNK_CACHE.exists():
        return []

    index = json.loads(CHUNK_CACHE.read_text(encoding="utf-8"))
    q_vec = embeddings.embed(job_text, task="RETRIEVAL_QUERY")
    if not q_vec:
        return []

    scored = [
        (embeddings.cosine_similarity(q_vec, item["vector"]), item["text"])
        for item in index
    ]
    scored.sort(reverse=True, key=lambda x: x[0])
    return [text for _score, text in scored[:top_k]]
