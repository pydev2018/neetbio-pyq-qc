"""
PYQ Matching QC App — Streamlit
Supports both Tier 1 (verbatim) and Tier 2 (section-grounded) matches.

Run:
    cd data_pipeline/qc_app
    streamlit run app.py
"""

import json
from pathlib import Path

import streamlit as st

# ─── Paths ──────────────────────────────────────────────────────────────────

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
MATCHED_FILE = DATA_DIR / "all_pyqs_matched.json"
ALL_PYQS_FILE = DATA_DIR / "pyqs_v2.json"
PARENTS_FILE = DATA_DIR / "parents_slim.json"

# ─── Load data ──────────────────────────────────────────────────────────────

@st.cache_data
def load_matched():
    return json.loads(MATCHED_FILE.read_text())

@st.cache_data
def load_all_pyqs():
    return json.loads(ALL_PYQS_FILE.read_text())

@st.cache_data
def load_parents():
    return json.loads(PARENTS_FILE.read_text())

# ─── App ────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="neet.bio — PYQ Match QC", layout="wide")
st.title("neet.bio — PYQ Matching QC")
st.caption("Review Tier 1 (verbatim) and Tier 2 (section-grounded) matches")

matched = load_matched()
all_pyqs = load_all_pyqs()
parents = load_parents()

# ─── Summary stats ──────────────────────────────────────────────────────────

total = len(matched)
n_verbatim = sum(1 for r in matched if r.get("classification") == "matched")
n_grounded = sum(1 for r in matched if r.get("classification") == "section_grounded")
n_discrepancy = sum(1 for r in matched if r.get("classification") == "claim_discrepancy_matched")
n_total_matched = n_verbatim + n_grounded + n_discrepancy
n_not_in = sum(1 for r in matched if r.get("classification") == "answer_not_in_ncert")
n_disagree = sum(1 for r in matched if r.get("claim_agrees_with_gpt") is False)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total", total)
col2.metric("All Matched", f"{n_total_matched} ({100*n_total_matched//max(1,total)}%)")
col3.metric("Tier 1 (Verbatim)", n_verbatim)
col4.metric("Tier 2 (Section)", n_grounded)
col5.metric("Not in NCERT", n_not_in)
col6.metric("GPT Disagreed", n_disagree)

st.divider()

# ─── Filters ────────────────────────────────────────────────────────────────

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    filter_class = st.selectbox("Classification", [
        "ALL", "matched", "section_grounded", "answer_not_in_ncert",
        "claim_discrepancy_matched", "pipeline_error"
    ])

with col_f2:
    filter_tier = st.selectbox("Tier", ["ALL", "Tier 1 (Verbatim)", "Tier 2 (Section)", "Not matched"])

with col_f3:
    filter_agree = st.selectbox("GPT Agrees?", ["ALL", "Yes", "No"])

filtered = matched
if filter_class != "ALL":
    filtered = [r for r in filtered if r.get("classification") == filter_class]
if filter_tier != "ALL":
    if filter_tier == "Tier 1 (Verbatim)":
        filtered = [r for r in filtered if r.get("classification") == "matched"]
    elif filter_tier == "Tier 2 (Section)":
        filtered = [r for r in filtered if r.get("classification") == "section_grounded"]
    elif filter_tier == "Not matched":
        filtered = [r for r in filtered if r.get("classification") == "answer_not_in_ncert"]
if filter_agree != "ALL":
    if filter_agree == "Yes":
        filtered = [r for r in filtered if r.get("claim_agrees_with_gpt") is True]
    else:
        filtered = [r for r in filtered if r.get("claim_agrees_with_gpt") is False]

st.write(f"Showing **{len(filtered)}** of {total} PYQs")

# ─── PYQ browser ────────────────────────────────────────────────────────────

if not filtered:
    st.info("No PYQs match the current filters.")
    st.stop()

pyq_idx = st.number_input("PYQ #", min_value=1, max_value=len(filtered), value=1, step=1)
r = filtered[pyq_idx - 1]

pyq_id = r.get("pyq_id", "")
pyq_data = all_pyqs.get(pyq_id, {})
cls = r.get("classification", "unknown")

# ─── Left / Right layout ───────────────────────────────────────────────────

left, right = st.columns([1, 1])

with left:
    st.subheader("Question")

    # Classification badge
    if cls == "matched":
        st.success("TIER 1 — VERBATIM MATCH (exact NCERT sentence found)")
    elif cls == "section_grounded":
        st.info("TIER 2 — SECTION GROUNDED (answer in this section, no single verbatim sentence)")
    elif cls == "answer_not_in_ncert":
        st.error("NOT IN NCERT (answer not found in any section)")
    elif cls == "claim_discrepancy_matched":
        st.warning("CLAIM DISCREPANCY (matched using GPT's corrected answer)")
    else:
        st.warning(f"{cls}")

    agrees = r.get("claim_agrees_with_gpt")
    if agrees is False:
        st.error(f"GPT DISAGREES with claimed answer key")

    st.write(f"**Year:** {r.get('year')} | **Type:** {r.get('pyq_type')} | **Source:** `{r.get('source_pdf', '')[:50]}`")
    st.write(f"**Chapter:** `{r.get('chapter_id', 'unknown')}` | **Section:** {r.get('section_title', 'unknown')}")

    st.divider()

    # Question text
    q_text = pyq_data.get("questionText") or r.get("question_preview") or "(no question text)"
    st.write("**QUESTION:**")
    st.text(q_text)

    st.write("")

    # Options
    options = pyq_data.get("options", [])
    claimed_key = r.get("claimed_correct_key", pyq_data.get("correctKey", ""))
    gpt_verification = r.get("gpt_verification") or {}
    gpt_key = gpt_verification.get("gpt_correct_key", "")

    if options:
        st.write("**OPTIONS:**")
        option_lines = []
        for opt in options:
            key = str(opt.get("key", "?"))
            text = str(opt.get("text", "(no text)"))
            is_claimed = (key == claimed_key)
            is_gpt = (key == gpt_key)

            if is_claimed and is_gpt:
                option_lines.append(f"  {key}  |  {text}  |  CORRECT (claimed + GPT agree)")
            elif is_claimed:
                option_lines.append(f"  {key}  |  {text}  |  CLAIMED CORRECT")
            elif is_gpt:
                option_lines.append(f"  {key}  |  {text}  |  GPT SAYS CORRECT")
            else:
                option_lines.append(f"  {key}  |  {text}  |")

        st.code("\n".join(option_lines), language=None)
    else:
        st.write("No options available")

    if not pyq_data:
        st.error(f"PYQ lookup failed for ID: {pyq_id}")

    # GPT reasoning
    if gpt_verification:
        st.caption(f"GPT reasoning: {gpt_verification.get('gpt_reasoning', '')} (confidence: {gpt_verification.get('gpt_confidence', '')})")

    # Fact extraction
    fact_ext = r.get("fact_extraction") or {}
    if fact_ext.get("fact"):
        st.divider()
        st.write("**Extracted fact (in NCERT language):**")
        st.info(fact_ext["fact"])
        if fact_ext.get("key_terms"):
            st.caption(f"Key terms: {', '.join(fact_ext['key_terms'])}")

with right:
    st.subheader("NCERT Match")

    parent_id = r.get("parent_block_id", "")
    parent = parents.get(parent_id, {})

    if cls == "matched":
        # ─── TIER 1: Verbatim ──────────────────────────────────────
        st.success("Tier 1 — Verbatim")

        st.write(f"**Parent block:** `{parent_id}`")
        st.write(f"**Section:** {parent.get('section_title', 'unknown')}")
        st.write(f"**Chapter:** `{parent.get('chapter_id', '')}`")

        span_text = r.get("answer_span_text", "")
        if span_text:
            st.write("**Verbatim NCERT sentence:**")
            st.warning(span_text)

        # Quote verifications
        verifs = r.get("quote_verifications", [])
        if verifs:
            st.write("**Verbatim verification:**")
            for v in verifs:
                ok = v.get("verbatim_ok", False)
                match_type = v.get("match_type", "unknown")
                if ok:
                    st.write(f"  :white_check_mark: `{match_type}` — byte-for-byte confirmed")
                else:
                    st.write(f"  :x: `{match_type}` — NOT FOUND")

        # Verification result
        vr = r.get("verification_result") or {}
        if vr.get("reason"):
            st.caption(f"Verification: {vr['confidence']} — {vr['reason']}")

        # Full parent content with span highlighted
        st.divider()
        st.write("**NCERT paragraph (answer highlighted):**")
        parent_content = parent.get("content", "")
        if parent_content and span_text and span_text in parent_content:
            before = parent_content[:parent_content.index(span_text)]
            after = parent_content[parent_content.index(span_text) + len(span_text):]
            st.text(before[-300:] if len(before) > 300 else before)
            st.warning(span_text)
            st.text(after[:300] if len(after) > 300 else after)
        elif parent_content:
            st.text(parent_content[:2000])

    elif cls == "section_grounded":
        # ─── TIER 2: Section Grounded ──────────────────────────────
        st.info("Tier 2 — Section Grounded")

        st.write(f"**Parent block:** `{parent_id}`")
        st.write(f"**Section:** {parent.get('section_title', 'unknown')}")
        st.write(f"**Chapter:** `{parent.get('chapter_id', '')}`")

        sg = r.get("section_grounding") or {}

        # Reasoning — the key QC item for Tier 2
        if sg.get("reasoning"):
            st.write("**How this section answers the question:**")
            st.success(sg["reasoning"])

        # Key facts used
        key_facts = sg.get("key_facts_used", [])
        if key_facts:
            st.write(f"**Key NCERT facts used ({len(key_facts)}):**")
            for i, f in enumerate(key_facts):
                st.write(f"  {i+1}. {f}")

        # Why not verbatim
        vr = r.get("verification_result") or {}
        why_not = vr.get("why_not_verbatim", "")
        if why_not:
            st.caption(f"Why not verbatim: {why_not}")

        # Confidence
        conf = sg.get("confidence", vr.get("confidence", ""))
        if conf:
            st.write(f"**Confidence:** {conf}")

        # Full parent content
        st.divider()
        st.write("**Full NCERT paragraph:**")
        parent_content = parent.get("content", "")
        if parent_content:
            st.text(parent_content[:2500])
        else:
            st.write("*(Parent content not available)*")

    elif cls == "answer_not_in_ncert":
        # ─── NOT MATCHED ───────────────────────────────────────────
        st.error("Not found in any NCERT section")
        st.write(f"**Notes:** {r.get('notes', '')}")

        # Show what was tried
        levels_tried = r.get("levels_tried", [])
        if levels_tried:
            st.write("**Search attempts:**")
            for lt in levels_tried:
                level = lt.get("level", "?")
                if "rejected" in str(level):
                    st.caption(f"  Rejected: {lt.get('verify_reason', '')[:120]}")
                elif level == "hybrid":
                    st.caption(f"  Hybrid search: {lt.get('candidates', 0)} candidates, fact: '{lt.get('fact', '')[:80]}...'")
                elif level == "section_grounded":
                    st.caption(f"  Section grounding attempted: confidence={lt.get('confidence', '?')}")
                else:
                    st.caption(f"  {level}")

    else:
        st.warning(f"Classification: {cls}")
        st.write(f"**Notes:** {r.get('notes', '')}")

    # Notes
    notes = r.get("notes", "")
    if notes:
        st.caption(notes)

# ─── Hybrid search scores (collapsible) ─────────────────────────────────────

with st.expander("Hybrid search scores"):
    scores = r.get("hybrid_scores", [])
    if scores:
        for s in scores:
            pid = s.get("parent_id", "?")
            p = parents.get(pid, {})
            st.write(
                f"  `{pid}` — combined={s.get('combined_score',0):.3f} "
                f"(kw={s.get('keyword_score',0):.2f}, emb={s.get('embedding_score',0):.2f}, "
                f"terms={s.get('keyword_terms_matched',0)}) "
                f"— {p.get('section_title', '')[:50]}"
            )
    else:
        st.write("No hybrid scores available")

# ─── Raw JSON (collapsible) ─────────────────────────────────────────────────

st.divider()

with st.expander("Raw match result JSON"):
    st.json(r)

with st.expander("Raw PYQ data JSON"):
    st.json(pyq_data)
