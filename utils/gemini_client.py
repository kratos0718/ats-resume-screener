import os
import json
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            key = ""
    if not key:
        raise ValueError("GROQ_API_KEY not set. Add it to .env or Streamlit secrets.")
    return key


def _client():
    from groq import Groq
    return Groq(api_key=_get_api_key())


MAIN_PROMPT = """You are an expert ATS (Applicant Tracking System) and career coach with 10 years experience helping candidates get past automated screening systems.

Analyse this resume against the job description and return ONLY valid JSON matching this exact schema:

{{
  "match_score": <integer 0-100>,
  "verdict": <"Poor Match" | "Needs Work" | "Good Match" | "Strong Match">,
  "summary": <one sentence summary of the match>,
  "keywords_present": [<list of matching keywords found in both>],
  "keywords_missing": [<list of important JD keywords missing from resume>],
  "sections": {{
    "summary": {{"rating": <"Strong"|"Average"|"Weak">, "feedback": <specific one-line feedback>}},
    "skills": {{"rating": <"Strong"|"Average"|"Weak">, "feedback": <specific one-line feedback>}},
    "experience": {{"rating": <"Strong"|"Average"|"Weak">, "feedback": <specific one-line feedback>}},
    "projects": {{"rating": <"Strong"|"Average"|"Weak">, "feedback": <specific one-line feedback>}},
    "education": {{"rating": <"Strong"|"Average"|"Weak">, "feedback": <specific one-line feedback>}}
  }},
  "improvements": [
    {{"rank": 1, "action": <specific action>, "effort": <"Quick Fix"|"Medium"|"Major Rework">, "impact": <"High"|"Medium">}},
    {{"rank": 2, "action": <specific action>, "effort": <"Quick Fix"|"Medium"|"Major Rework">, "impact": <"High"|"Medium">}},
    {{"rank": 3, "action": <specific action>, "effort": <"Quick Fix"|"Medium"|"Major Rework">, "impact": <"High"|"Medium">}}
  ],
  "bullets": [<extract up to 8 experience or project bullet points verbatim from the resume text>]
}}

Job Description:
{job_description}

Resume Text:
{resume_text}

Return ONLY the JSON. No explanation, no markdown, no preamble."""


BULLET_PROMPT = """You are an expert resume writer. Rewrite this resume bullet point to be stronger and more relevant for the job description provided.

Rules:
- Keep it to ONE bullet point (one line)
- Start with a strong action verb
- Include relevant keywords from the job description naturally
- Add quantification if possible (%, numbers, scale)
- Keep the same core achievement — don't invent fake accomplishments
- Maximum 25 words

Original bullet: {bullet}
Job description keywords to include: {top_keywords}

Return ONLY the rewritten bullet. Nothing else."""


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned invalid JSON: {e}\n\nRaw response:\n{raw[:500]}")


def analyse_resume(job_description: str, resume_text: str) -> dict:
    prompt = MAIN_PROMPT.format(job_description=job_description, resume_text=resume_text)
    response = _client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return _parse_json(response.choices[0].message.content)


def rewrite_bullet(bullet: str, top_keywords: list[str]) -> str:
    prompt = BULLET_PROMPT.format(
        bullet=bullet,
        top_keywords=", ".join(top_keywords[:12]),
    )
    response = _client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
