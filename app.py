"""
PYQ Matching QC App — Streamlit
For reviewing the 200 QC PYQ matches against original NCERT sections.

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
ALL_PYQS_FILE = DATA_DIR / "pyqs_slim.json"
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
st.caption("Review PYQ to NCERT matches for accuracy. Your wife's QC dashboard.")

matched = load_matched()
all_pyqs = load_all_pyqs()
parents = load_parents()

# ─── Summary stats ──────────────────────────────────────────────────────────

total = len(matched)
n_matched = sum(1 for r in matched if r.get("matched"))
n_l1 = sum(1 for r in matched if r.get("level_at_success") == 1)
n_l2 = sum(1 for r in matched if r.get("level_at_success") == 2)
n_l3 = sum(1 for r in matched if r.get("level_at_success") == 3)
n_not_in = sum(1 for r in matched if r.get("classification") == "answer_not_in_ncert")
n_disagree = sum(1 for r in matched if r.get("claim_agrees_with_gpt") is False)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total", total)
col2.metric("Matched", f"{n_matched} ({100*n_matched//max(1,total)}%)")
col3.metric("L1 / L2 / L3", f"{n_l1} / {n_l2} / {n_l3}")
col4.metric("Not in NCERT", n_not_in)
col5.metric("GPT Disagreed", n_disagree)

st.divider()

# ─── Filters ────────────────────────────────────────────────────────────────

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    filter_class = st.selectbox("Classification", [
        "ALL", "matched", "answer_not_in_ncert", "claim_discrepancy_matched", "pipeline_error"
    ])

with col_f2:
    filter_level = st.selectbox("Level", ["ALL", "1", "2", "3", "None"])

with col_f3:
    filter_agree = st.selectbox("GPT Agrees?", ["ALL", "Yes", "No"])

filtered = matched
if filter_class != "ALL":
    filtered = [r for r in filtered if r.get("classification") == filter_class]
if filter_level != "ALL":
    if filter_level == "None":
        filtered = [r for r in filtered if r.get("level_at_success") is None]
    else:
        filtered = [r for r in filtered if r.get("level_at_success") == int(filter_level)]
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

# ─── Left / Right layout ───────────────────────────────────────────────────

left, right = st.columns([1, 1])

with left:
    st.subheader("Question")

    # Classification badge
    cls = r.get("classification", "unknown")
    level = r.get("level_at_success")
    agrees = r.get("claim_agrees_with_gpt")

    if cls == "matched":
        st.success(f"MATCHED at Level {level} | GPT Agrees: {agrees}")
    elif cls == "answer_not_in_ncert":
        st.error(f"NOT IN NCERT | GPT Agrees: {agrees}")
    elif cls == "claim_discrepancy_matched":
        st.warning(f"CLAIM DISCREPANCY (matched with GPT's answer) | GPT Agrees: {agrees}")
    else:
        st.info(f"{cls} | Level: {level} | GPT Agrees: {agrees}")

    st.write(f"**Year:** {r.get('year')} | **Type:** {r.get('pyq_type')} | **Source:** `{r.get('source_pdf', '')[:50]}`")
    st.write(f"**Chapter assigned:** `{r.get('chapter_id', 'unknown')}`")

    st.divider()

    # Question text — use st.write for safety, fallback to question_preview
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
        for opt in options:
            key = str(opt.get("key", "?"))
            text = str(opt.get("text", "(no text)"))
            is_claimed = (key == claimed_key)
            is_gpt = (key == gpt_key)

            if is_claimed and is_gpt:
                label = "CORRECT"
            elif is_claimed:
                label = "CLAIMED"
            elif is_gpt:
                label = "GPT ANSWER"
            else:
                label = ""

            # Build the display line
            option_line = f"{key}. {text}"

            if is_claimed or is_gpt:
                color = "green" if is_claimed else "orange"
                st.markdown(f":{color}[**{option_line}** --- {label}]")
            else:
                st.text(option_line)
    else:
        st.write("No options available")

    if not pyq_data:
        st.error(f"PYQ lookup failed for ID: {pyq_id}")

    # GPT reasoning
    if gpt_verification:
        st.caption(f"GPT reasoning: {gpt_verification.get('gpt_reasoning', '')} (confidence: {gpt_verification.get('gpt_confidence', '')})")

    # Explanation from original PYQ
    explanation = pyq_data.get("explanation", "")
    if explanation:
        st.divider()
        st.write("**Original explanation:**")
        st.caption(explanation)

with right:
    st.subheader("NCERT Match")

    if r.get("matched"):
        parent_id = r.get("parent_block_id", "")
        parent = parents.get(parent_id, {})

        st.write(f"**Parent block:** `{parent_id}`")
        st.write(f"**Section:** {parent.get('section_title', 'unknown')}")
        st.write(f"**Chapter:** `{parent.get('chapter_id', '')}`")

        # Answer span — the key thing to QC
        span_text = r.get("answer_span_text", "")
        if span_text:
            st.write("**Answer span (verbatim from NCERT):**")
            st.info(span_text)

        # All quotes
        all_quotes = r.get("all_quotes", [])
        if len(all_quotes) > 1:
            st.write(f"**All extracted quotes ({len(all_quotes)}):**")
            for i, q in enumerate(all_quotes):
                st.write(f"  {i+1}. _{q}_")

        # Quote verifications
        verifs = r.get("quote_verifications", [])
        if verifs:
            st.write("**Verbatim verification:**")
            for v in verifs:
                ok = v.get("verbatim_ok", False)
                match_type = v.get("match_type", "unknown")
                if ok:
                    st.write(f"  :white_check_mark: `{match_type}` — offsets [{v.get('relative_start')}, {v.get('relative_end')}]")
                else:
                    st.write(f"  :x: `{match_type}` — NOT FOUND in parent text")

        # Full parent content with span highlighted
        st.divider()
        st.write("**Full NCERT parent block (answer highlighted):**")
        parent_content = parent.get("content", "")
        if parent_content:
            if span_text and span_text in parent_content:
                # Split around the span and show with highlight
                before = parent_content[:parent_content.index(span_text)]
                after = parent_content[parent_content.index(span_text) + len(span_text):]
                st.text(before[-200:] if len(before) > 200 else before)
                st.warning(span_text)
                st.text(after[:200] if len(after) > 200 else after)
            else:
                st.text(parent_content[:2000])
        else:
            st.write("*(Parent content not available)*")

        st.caption(r.get("notes", ""))

    else:
        st.error(f"Not matched: {cls}")
        st.write(f"**Notes:** {r.get('notes', '')}")

        # Show what levels were tried
        levels_tried = r.get("levels_tried", [])
        if levels_tried:
            st.write("**Levels tried:**")
            for lt in levels_tried:
                st.caption(f"Level {lt.get('level')}: query='{lt.get('query', '')[:80]}...', parents_tried={lt.get('parents_tried')}")

# ─── Raw JSON (collapsible) ─────────────────────────────────────────────────

st.divider()

with st.expander("Raw match result JSON"):
    st.json(r)

with st.expander("Raw PYQ data JSON"):
    st.json(pyq_data)
