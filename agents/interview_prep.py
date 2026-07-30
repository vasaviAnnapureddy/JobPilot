# -*- coding: utf-8 -*-
"""
INTERVIEW-PREP AGENT — your personal interview coach.

Four things it does, all grounded in YOUR real resume (via RAG):

  1. company_brief(company, role)  — you ask about a company; it explains
     what they build, why they'd need someone like you, and how YOUR
     experience helps them. (Your stated top priority.)
  2. mock_questions(role, jd)      — likely technical + HR questions for a role.
  3. answer_feedback(question, ans)— you paste a practice answer; it rates it
     and shows how to improve.
  4. vocabulary(text)              — stronger, more professional phrasing.

Honest note: "company brief" uses the model's knowledge + your resume. It is
not live web scraping of the company's site. For a fast-moving company, verify
key facts. (Live web research is a future enhancement.)
"""

from core import db, llm, rag


def _evidence(query):
    rag.build_index()
    hits = rag.retrieve(query, top_k=3)
    return " || ".join(hits) if hits else "(general AI/ML fresher profile)"


def company_brief(company, role=""):
    ev = _evidence(f"{role} at {company}")
    prompt = f"""You are helping Vasavi, a fresher AI/ML engineer, prepare for an interview.
Give a clear, honest briefing about this company for her interview.

COMPANY: {company}
ROLE she may interview for: {role or "(not specified)"}
VASAVI'S RELEVANT REAL EXPERIENCE (from her resume): {ev}

Write the brief in simple English with these sections (use short bullet points):
1. What the company does — products/services, industry.
2. Why a company like this needs someone with Vasavi's skills.
3. How Vasavi's specific experience (from the evidence above) helps them — be concrete.
4. 3 smart questions Vasavi can ask the interviewer.
If you are unsure about a specific fact, say "verify this" rather than guessing.
Keep it under 300 words. Output plain text with clear headings."""
    ans = llm.ask(prompt, log_fn=lambda m: db.log("interview", m, "WARN"))
    _save("company_brief", company, role, "", ans)
    return ans


def mock_questions(role, jd=""):
    ev = _evidence(role + " " + jd[:300])
    prompt = f"""Generate interview questions for this role, tailored to a fresher.
ROLE: {role}
JOB CONTEXT: {jd[:600]}
CANDIDATE'S REAL EXPERIENCE: {ev}

Give:
- 6 technical questions they are likely to ask (mix of easy and medium).
- 4 HR / behavioural questions.
- For 2 of the technical questions, add a one-line hint on how she should approach it using her real experience.
Output as a clean numbered list under two headings: TECHNICAL and HR."""
    ans = llm.ask(prompt, log_fn=lambda m: db.log("interview", m, "WARN"))
    _save("mock_questions", "", role, jd[:200], ans)
    return ans


def answer_feedback(question, answer):
    prompt = f"""You are an interview coach. Rate this practice answer and help improve it.
QUESTION: {question}
CANDIDATE'S ANSWER: {answer}

Give:
1. Score out of 10.
2. What was good (1-2 points).
3. What to improve (2-3 specific points).
4. A rewritten, stronger version of the answer (concise, confident, professional).
Be kind but honest. Simple English."""
    ans = llm.ask(prompt, log_fn=lambda m: db.log("interview", m, "WARN"))
    _save("answer_feedback", "", "", question, ans)
    return ans


CONCEPT_TOPICS = {
    "ai_ml":    ["Machine Learning basics", "Overfitting & regularization", "Bias-variance tradeoff",
                 "Gradient descent", "Ensemble methods (Random Forest, XGBoost)", "Cross-validation"],
    "deep_learning": ["Neural networks", "Backpropagation", "CNNs", "RNNs & LSTMs",
                      "Transformers & attention", "Activation functions"],
    "genai":    ["LLMs & tokens", "RAG", "Prompt engineering", "Fine-tuning vs RAG",
                 "Embeddings & vector databases", "Hallucination & how to reduce it"],
    "stats":    ["p-value & hypothesis testing", "Probability distributions", "Central Limit Theorem",
                 "Correlation vs causation", "A/B testing", "Bayes theorem"],
    "data":     ["SQL joins", "Normalization", "ETL pipelines", "Pandas operations",
                 "Feature engineering", "Handling missing data"],
    "coding":   ["Time & space complexity (Big-O)", "Arrays & hashing", "Two pointers",
                 "Recursion", "Dynamic programming basics", "Trees & graphs"],
}


def concept_coach(topic):
    """Teach any interview topic clearly + quiz the user on it."""
    prompt = f"""You are teaching a fresher AI/ML engineer for interviews. Explain this topic
clearly in simple English, then quiz her.

TOPIC: {topic}

Give:
1. SIMPLE EXPLANATION — 4-6 lines, like explaining to a beginner, with a small real example.
2. WHY INTERVIEWERS ASK IT — 1 line.
3. 3 LIKELY INTERVIEW QUESTIONS on this topic (increasing difficulty).
4. THE ANSWER to question 1 (so she can check herself).
Use clear headings. Keep it under 320 words."""
    ans = llm.ask(prompt, log_fn=lambda m: db.log("interview", m, "WARN"))
    _save("concept_coach", "", topic, topic, ans)
    return ans


def vocabulary(text):
    prompt = f"""Improve the professional vocabulary and phrasing of this text a fresher would
say in an interview. Keep her meaning, make it sound confident and polished, not fake.

TEXT: {text}

Give:
1. A polished version.
2. 5 stronger words/phrases she can reuse (word -> better word).
Simple English."""
    ans = llm.ask(prompt, log_fn=lambda m: db.log("interview", m, "WARN"))
    _save("vocabulary", "", "", text[:200], ans)
    return ans


def interview_chat(messages, role="AI/ML Engineer"):
    """
    A REAL back-and-forth mock interview. `messages` is the conversation so far:
    a list of {"role": "user"|"assistant", "content": "..."}.
    Returns the interviewer's next single message (asks, reacts, corrects, follows up).
    """
    # personalise with her real resume the first time
    ev = _evidence(role)
    transcript = ""
    for m in messages:
        who = "Interviewer" if m.get("role") == "assistant" else "Candidate"
        transcript += f"{who}: {m.get('content','')}\n"

    if not messages:
        transcript = "(the interview is just starting)"

    prompt = f"""You are a friendly but real interviewer conducting a live mock interview for
Vasavi, a fresher applying for a {role} role. Her real background: {ev}

HOW TO BEHAVE (very important):
- Talk like a real human interviewer, warm and natural. Short messages (2-5 sentences).
- Ask ONE question at a time, then WAIT.
- After she answers: briefly react, GENTLY correct any mistake or weak point, give a quick tip,
  then ask a natural follow-up OR move to the next question.
- Sometimes dig deeper into her real projects. If she struggles, guide her kindly.
- Do NOT list many questions at once. Do NOT write paragraphs. Keep it conversational.
- If this is the start, greet her warmly and ask the first question.

Conversation so far:
{transcript}

Now write ONLY the interviewer's next message (nothing else):"""
    return llm.ask(prompt, log_fn=lambda m: db.log("interview", m, "WARN"))


def _save(kind, company, role, question, response):
    try:
        db.get_client().table("interview_prep").insert({
            "kind": kind, "company": company, "role": role,
            "question": question[:1000], "response_md": response[:5000],
        }).execute()
    except Exception:
        pass   # table may not exist yet (before migration) — feature still returns the answer
