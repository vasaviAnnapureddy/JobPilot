# -*- coding: utf-8 -*-
"""
PROFILES — dynamic, user-named resumes.

You are NOT limited to fixed slots. You add a resume, give it any NAME
(e.g. "Computer Vision", "MLOps", "Data Analyst"), and the system:
  - saves it as its own file (cv_<slug>.md)
  - remembers the name in profiles.json
  - builds job searches from that name
  - matches those jobs against that resume (its own RAG index)

Stored on disk (no database migration needed):
  data/resumes/profiles.json      -> {slug: {name, searches}}
  data/resumes/cv_<slug>.md       -> the resume text
"""

import json
import re
from core import config

REG = config.RESUMES_DIR / "profiles.json"


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return s[:40] or "resume"


def searches_for(name):
    """Turn a resume name into a set of fresher job searches."""
    n = (name or "").strip().lower() or "ai ml"
    return [f"{n} fresher", f"{n} entry level", f"junior {n}",
            f"{n} intern", f"{n} 2025 batch", f"{n} associate"]


def _load():
    if REG.exists():
        try:
            return json.loads(REG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(d):
    REG.parent.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(d, indent=2), encoding="utf-8")


def list_profiles():
    """Return all resumes the user has added."""
    d = _load()
    out = []
    for slug, meta in d.items():
        path = config.RESUMES_DIR / f"cv_{slug}.md"
        out.append({
            "slug": slug,
            "name": meta.get("name", slug),
            "searches": meta.get("searches") or searches_for(meta.get("name", slug)),
            "chars": len(path.read_text(encoding="utf-8")) if path.exists() else 0,
        })
    return out


def add_profile(name, text):
    """Add or update a named resume. Returns its slug."""
    slug = slugify(name)
    d = _load()
    d[slug] = {"name": (name or slug).strip(), "searches": searches_for(name)}
    _save(d)
    path = config.RESUMES_DIR / f"cv_{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return slug


def delete_profile(slug):
    d = _load()
    if slug in d:
        del d[slug]
        _save(d)
    path = config.RESUMES_DIR / f"cv_{slug}.md"
    if path.exists():
        path.unlink()


def label_for(slug):
    """Human name for a slug (for showing tabs)."""
    d = _load()
    if slug in d:
        return d[slug].get("name", slug)
    # fall back to the old fixed profiles if any
    meta = config.RESUME_PROFILES.get(slug)
    return meta["label"] if meta else slug
