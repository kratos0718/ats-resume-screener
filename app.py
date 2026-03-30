import random
import streamlit as st

from utils.pdf_parser import extract_text_from_pdf
from utils.gemini_client import analyse_resume, rewrite_bullet

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ATS Resume Screener",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS — vibrant dark UI ───────────────────────────────────────────────
st.markdown("""
<style>
/* Gradient hero title */
.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6366F1, #A855F7, #EC4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
}
.hero-sub {
    color: #94A3B8;
    font-size: 1.05rem;
    margin-bottom: 1.5rem;
}

/* Score ring */
.score-ring {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 180px;
    height: 180px;
    border-radius: 50%;
    border: 8px solid;
    font-size: 3rem;
    font-weight: 900;
    line-height: 1;
}

/* Verdict badge */
.verdict-badge {
    display: inline-block;
    padding: 8px 22px;
    border-radius: 30px;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 10px;
}

/* Keyword pill */
.kw-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 3px 3px;
}
.kw-present {
    background: #052E16;
    color: #4ADE80;
    border: 1px solid #16A34A;
}
.kw-missing {
    background: #450A0A;
    color: #F87171;
    border: 1px solid #DC2626;
}

/* Section table row */
.section-card {
    background: #1A1A2E;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    border-left: 4px solid;
    display: flex;
    align-items: flex-start;
    gap: 14px;
}
.rating-chip {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    white-space: nowrap;
}

/* Improvement card */
.imp-card {
    background: linear-gradient(135deg, #1E1B4B, #1A1A2E);
    border: 1px solid #3730A3;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
}
.imp-rank {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366F1, #A855F7);
    font-weight: 800;
    font-size: 0.9rem;
    color: white;
    flex-shrink: 0;
    margin-right: 12px;
}
.effort-tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-right: 6px;
}

/* Bullet card */
.bullet-card {
    background: #12122A;
    border: 1px solid #2D2B55;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.bullet-original { color: #94A3B8; font-size: 0.9rem; }
.bullet-rewritten {
    color: #A5F3FC;
    font-size: 0.9rem;
    border-left: 3px solid #06B6D4;
    padding-left: 10px;
    margin-top: 8px;
}

/* Section divider */
.section-header {
    font-size: 1.3rem;
    font-weight: 700;
    color: #E2E8F0;
    margin: 2rem 0 1rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #2D2B55;
}
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">ATS Resume Screener</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Paste a job description + upload your resume — get your ATS score, '
    'missing keywords, section feedback, and AI-rewritten bullets in seconds.</div>',
    unsafe_allow_html=True,
)

# ── Input columns ──────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("**Job Description**")
    job_description = st.text_area(
        label="jd",
        label_visibility="collapsed",
        placeholder="Paste the full job description here…",
        height=300,
    )
    char_count = len(job_description)
    if char_count == 0:
        st.caption("0 characters — paste the job description above")
    elif char_count < 200:
        st.markdown(
            f"<small style='color:#F87171'>{char_count} characters — add more for better analysis</small>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<small style='color:#4ADE80'>{char_count} characters ✓</small>",
            unsafe_allow_html=True,
        )

with col_right:
    st.markdown("**Your Resume (PDF)**")
    uploaded_file = st.file_uploader(
        label="resume",
        label_visibility="collapsed",
        type=["pdf"],
    )
    if uploaded_file is not None:
        try:
            import PyPDF2, io
            reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
            page_count = len(reader.pages)
            uploaded_file.seek(0)
            st.success(f"**{uploaded_file.name}** — {page_count} page{'s' if page_count != 1 else ''} loaded ✓")
        except Exception:
            st.info(f"**{uploaded_file.name}** loaded")

# ── Analyse button ─────────────────────────────────────────────────────────────
st.markdown("")
both_provided = bool(job_description.strip()) and uploaded_file is not None

analyse_clicked = st.button(
    "✨ Analyse My Resume",
    type="primary",
    disabled=not both_provided,
    use_container_width=True,
)

if not both_provided:
    missing = []
    if not job_description.strip():
        missing.append("job description")
    if uploaded_file is None:
        missing.append("resume PDF")
    st.caption(f"Waiting for: {' and '.join(missing)}")

# ── On button click ────────────────────────────────────────────────────────────
if analyse_clicked and both_provided:
    loading_messages = [
        "Reading your resume...",
        "Scanning job requirements...",
        "Matching keywords...",
        "Calculating your ATS score...",
        "Preparing your personalised feedback...",
    ]
    with st.spinner(random.choice(loading_messages)):
        resume_text = extract_text_from_pdf(uploaded_file)
        if not resume_text or len(resume_text) < 100:
            st.error("Could not extract text from this PDF. Try a different PDF or paste your resume as text.")
            st.stop()

        if len(job_description) < 200:
            st.warning("Job description seems short. Add more details for better analysis.")

        try:
            result = analyse_resume(job_description, resume_text)
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

        st.session_state["analysis"] = result
        st.session_state["rewrites"] = {}
        st.session_state["jd_text"] = job_description

# ══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════════
if "analysis" not in st.session_state:
    st.stop()

data = st.session_state["analysis"]
match_score  = data.get("match_score", 0)
verdict      = data.get("verdict", "")
summary      = data.get("summary", "")
kw_present   = data.get("keywords_present", [])[:15]
kw_missing   = data.get("keywords_missing", [])[:15]
sections     = data.get("sections", {})
improvements = data.get("improvements", [])
bullets      = data.get("bullets", [])
jd_text      = st.session_state.get("jd_text", "")

# ── Score colours ──────────────────────────────────────────────────────────────
if match_score <= 40:
    score_color = "#F87171"; badge_bg = "#450A0A"; badge_text = "#FCA5A5"
elif match_score <= 65:
    score_color = "#FB923C"; badge_bg = "#431407"; badge_text = "#FED7AA"
elif match_score <= 85:
    score_color = "#4ADE80"; badge_bg = "#052E16"; badge_text = "#86EFAC"
else:
    score_color = "#34D399"; badge_bg = "#022C22"; badge_text = "#6EE7B7"

# ── Feature 2 — Score Display ──────────────────────────────────────────────────
st.markdown('<div class="section-header">Your ATS Analysis</div>', unsafe_allow_html=True)

score_col, verdict_col, _ = st.columns([1, 2, 1])

with score_col:
    st.markdown(
        f"""<div class="score-ring" style="border-color:{score_color}; color:{score_color};">
            {match_score}%<br>
            <span style="font-size:0.85rem; font-weight:500; color:#94A3B8">match</span>
        </div>""",
        unsafe_allow_html=True,
    )

with verdict_col:
    st.markdown(
        f"""<div class="verdict-badge" style="background:{badge_bg}; color:{badge_text}; border:2px solid {score_color};">
            {verdict}
        </div>
        <p style="color:#CBD5E1; font-size:0.95rem; margin-top:8px;">{summary}</p>""",
        unsafe_allow_html=True,
    )

# ── Feature 3 — Keyword Analysis ──────────────────────────────────────────────
st.markdown('<div class="section-header">Keyword Analysis</div>', unsafe_allow_html=True)

kw_left, kw_right = st.columns(2)

with kw_left:
    st.markdown(
        "<p style='color:#4ADE80; font-weight:700; font-size:1rem;'>✅ Keywords You Have</p>",
        unsafe_allow_html=True,
    )
    if kw_present:
        pills = " ".join(
            f'<span class="kw-pill kw-present">{kw}</span>' for kw in kw_present
        )
        st.markdown(pills, unsafe_allow_html=True)
    else:
        st.caption("No matching keywords found.")

with kw_right:
    st.markdown(
        "<p style='color:#F87171; font-weight:700; font-size:1rem;'>❌ Keywords You're Missing</p>",
        unsafe_allow_html=True,
    )
    if kw_missing:
        pills = " ".join(
            f'<span class="kw-pill kw-missing">{kw}</span>' for kw in kw_missing
        )
        st.markdown(pills, unsafe_allow_html=True)
    else:
        st.caption("No critical keywords missing — great!")

# ── Feature 4 — Section-by-Section Analysis ───────────────────────────────────
st.markdown('<div class="section-header">Section-by-Section Feedback</div>', unsafe_allow_html=True)

SECTION_LABELS = {
    "summary":    "Summary / Objective",
    "skills":     "Skills",
    "experience": "Experience",
    "projects":   "Projects",
    "education":  "Education",
}
RATING_STYLES = {
    "Strong":  ("border-color:#4ADE80", "background:#052E16; color:#4ADE80"),
    "Average": ("border-color:#FB923C", "background:#431407; color:#FB923C"),
    "Weak":    ("border-color:#F87171", "background:#450A0A; color:#F87171"),
}

for key, label in SECTION_LABELS.items():
    sec = sections.get(key, {})
    rating   = sec.get("rating", "Average")
    feedback = sec.get("feedback", "—")
    border_style, chip_style = RATING_STYLES.get(rating, RATING_STYLES["Average"])

    st.markdown(
        f"""<div class="section-card" style="{border_style}">
            <div style="min-width:120px">
                <div style="color:#E2E8F0; font-weight:700; font-size:0.9rem; margin-bottom:6px">{label}</div>
                <span class="rating-chip" style="{chip_style}">{rating}</span>
            </div>
            <div style="color:#94A3B8; font-size:0.88rem; padding-top:4px">{feedback}</div>
        </div>""",
        unsafe_allow_html=True,
    )

# ── Feature 5 — Bullet Rewriter ────────────────────────────────────────────────
if bullets:
    st.markdown('<div class="section-header">AI Bullet Rewriter</div>', unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#94A3B8; font-size:0.9rem; margin-bottom:1rem'>"
        "Click <b>Rewrite</b> on any bullet to get a stronger, keyword-targeted version tailored to this JD.</p>",
        unsafe_allow_html=True,
    )

    rewrites = st.session_state.get("rewrites", {})

    for i, bullet in enumerate(bullets):
        rewritten = rewrites.get(i)

        st.markdown(
            f'<div class="bullet-card">'
            f'<div class="bullet-original">• {bullet}</div>'
            + (
                f'<div class="bullet-rewritten">✨ {rewritten}</div>'
                if rewritten else ""
            )
            + "</div>",
            unsafe_allow_html=True,
        )

        btn_col, copy_col = st.columns([1, 4])
        with btn_col:
            if st.button(
                "Rewrite" if not rewritten else "Re-rewrite",
                key=f"rewrite_btn_{i}",
                use_container_width=True,
            ):
                with st.spinner("Rewriting bullet..."):
                    try:
                        new_bullet = rewrite_bullet(bullet, kw_missing + kw_present)
                        st.session_state["rewrites"][i] = new_bullet
                        st.rerun()
                    except Exception:
                        st.error("Rewrite failed. Try again.")

        if rewritten:
            with copy_col:
                st.code(rewritten, language=None)

# ── Feature 6 — Top 3 Improvements ───────────────────────────────────────────
if improvements:
    st.markdown('<div class="section-header">Top 3 Improvements</div>', unsafe_allow_html=True)

    EFFORT_STYLES = {
        "Quick Fix":    "background:#052E16; color:#4ADE80",
        "Medium":       "background:#431407; color:#FB923C",
        "Major Rework": "background:#450A0A; color:#F87171",
    }
    IMPACT_STYLES = {
        "High":   "background:#1E1B4B; color:#A5B4FC",
        "Medium": "background:#1C1917; color:#D6D3D1",
    }

    for imp in improvements:
        rank   = imp.get("rank", "")
        action = imp.get("action", "")
        effort = imp.get("effort", "")
        impact = imp.get("impact", "")

        effort_style = EFFORT_STYLES.get(effort, EFFORT_STYLES["Medium"])
        impact_style = IMPACT_STYLES.get(impact, IMPACT_STYLES["Medium"])

        st.markdown(
            f"""<div class="imp-card">
                <div style="display:flex; align-items:flex-start; gap:12px">
                    <div class="imp-rank">{rank}</div>
                    <div style="flex:1">
                        <div style="color:#E2E8F0; font-size:0.95rem; margin-bottom:10px">{action}</div>
                        <span class="effort-tag" style="{effort_style}">{effort}</span>
                        <span class="effort-tag" style="{impact_style}">Impact: {impact}</span>
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#475569; font-size:0.8rem'>"
    "Built with Streamlit + Google Gemini 1.5 Flash · No data stored · Free to use</p>",
    unsafe_allow_html=True,
)
