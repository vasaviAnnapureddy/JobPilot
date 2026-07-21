# -*- coding: utf-8 -*-
"""
JobPilot — the AI engine with a FALLBACK CHAIN.

Order of attempts (stops at first success):
  1. Gemini key 1, flash-lite
  2. Gemini key 1, flash
  3. Gemini key 2, flash-lite
  4. Gemini key 2, flash
  5. Groq llama-3.3-70b  (different company entirely — its quota
     is separate, so when Google says no, Groq says yes)

This is why the system will never again die with
"429 RESOURCE_EXHAUSTED" in the middle of a run.
"""

import json
import re
import time
from core import config


def _try_gemini(api_key, model, prompt):
    from google import genai
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(model=model, contents=prompt)
    return resp.text.strip()


def _try_groq(prompt):
    from groq import Groq
    client = Groq(api_key=config.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def ask(prompt, log_fn=None):
    """
    Ask the AI. Walks the fallback chain until someone answers.
    Returns the text answer, or raises RuntimeError if ALL models failed.
    """
    def _log(msg):
        if log_fn:
            log_fn(msg)

    # Gemini attempts: every key × every model
    for key_idx, api_key in enumerate(config.GEMINI_KEYS, 1):
        for model in config.GEMINI_MODELS:
            try:
                return _try_gemini(api_key, model, prompt)
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err or "503" in err:
                    _log(f"Gemini key{key_idx}/{model} busy — trying next in chain")
                    continue
                if "404" in err:  # model renamed/retired
                    _log(f"Gemini model {model} not found — trying next")
                    continue
                raise  # real error (bad key etc.) — don't hide it

    # Groq — the backup brain
    if config.GROQ_READY:
        try:
            _log("All Gemini options busy — switching to Groq backup")
            return _try_groq(prompt)
        except Exception as e:
            _log(f"Groq also failed: {str(e)[:80]}")

    raise RuntimeError("Every model in the fallback chain is unavailable right now.")


def ask_json(prompt, log_fn=None, retries=2):
    """
    Ask the AI and parse the answer as JSON.
    Retries with a stern reminder if the model returns broken JSON.
    """
    for attempt in range(retries + 1):
        text = ask(prompt, log_fn=log_fn)
        # Strip markdown fences if present
        cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Sometimes there's text around the JSON — extract the array/object
            match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            if attempt < retries:
                prompt = prompt + "\n\nIMPORTANT: Reply with ONLY valid JSON. No explanation, no markdown."
                time.sleep(2)

    raise ValueError("Model kept returning invalid JSON.")
