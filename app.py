"""
PYQ Matching QC App — Streamlit
For reviewing the 200 QC PYQ matches against original NCERT sections.

Run:
    cd data_pipeline/qc_app
    streamlit run app.py
"""

import json
import os
from pathlib import Path

import streamlit as st

# ─── Paths ──────────────────────────────────────────────────────────────────

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
MATCHED_FILE = DATA_DIR / "all_pyqs_matched.json"
ALL_PYQS_FILE = DATA_DIR / "all_pyqs.json"
PARENTS_FILE = DATA_DIR / "parents_slim.json"

# ─── Load data ──────────────────────────────────────────────────────────────

@st.cache_data
def load_matched():
    return json.loads(MATCHED_FILE.read_text())

@st.cache_data
def load_all_pyqs():
    pyqs = json.loads(ALL_PYQS_FILE.read_text())
    return {p["id"]: p for p in pyqs}

@st.cache_data
def load_parents():
    return json.loads(PARENTS_FILE.read_text())

# ─── App ────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="PYQ Match QC", layout="wide")
st.title("PYQ Matching QC")
st.caption("Review PYQ → NCERT matches for accuracy")

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

    badge_color = {"matched": "green", "answer_not_in_ncert": "red", "claim_discrepancy_matched": "orange"}.get(cls, "gray")
    st.markdown(f"**Status:** :{badge_color}[{cls}] | **Level:** {level} | **GPT Agrees:** {agrees}")

    st.markdown(f"**Year:** {r.get('year')} | **Type:** {r.get('pyq_type')} | **Source:** {r.get('source_pdf', '')[:40]}")
    st.markdown(f"**Chapter:** `{r.get('chapter_id', 'unknown')}`")

    st.markdown("---")

    # Question text
    q_text = pyq_data.get("questionText", r.get("question_preview", ""))
    st.markdown(f"**Q:** {q_text}")

    # Options
    options = pyq_data.get("options", [])
    claimed_key = r.get("claimed_correct_key", "")
    gpt_key = r.get("gpt_verification", {}).get("gpt_correct_key", "") if r.get("gpt_verification") else ""

    for opt in options:
        key = opt.get("key", "")
        text = opt.get("text", "")
        marker = ""
        if key == claimed_key:
            marker = " :green[<-- claimed correct]"
        if key == gpt_key and gpt_key != claimed_key:
            marker += " :orange[<-- GPT says correct]"
        st.markdown(f"**{key})** {text}{marker}")

    if r.get("gpt_verification"):
        gv = r["gpt_verification"]
        st.caption(f"GPT reasoning: {gv.get('gpt_reasoning', '')} (confidence: {gv.get('gpt_confidence', '')})")

with right:
    st.subheader("NCERT Match")

    if r.get("matched"):
        parent_id = r.get("parent_block_id", "")
        parent = parents.get(parent_id, {})

        st.markdown(f"**Parent block:** `{parent_id}`")
        st.markdown(f"**Section:** {parent.get('section_title', 'unknown')}")
        st.markdown(f"**Chapter:** `{parent.get('chapter_id', '')}`")

        # Answer span
        span_text = r.get("answer_span_text", "")
        if span_text:
            st.markdown("**Answer span (verbatim from NCERT):**")
            st.info(span_text)

        # All quotes
        all_quotes = r.get("all_quotes", [])
        if len(all_quotes) > 1:
            st.markdown(f"**All quotes ({len(all_quotes)}):**")
            for i, q in enumerate(all_quotes):
                st.markdown(f"{i+1}. {q}")

        # Quote verifications
        verifs = r.get("quote_verifications", [])
        if verifs:
            st.markdown("**Verification:**")
            for v in verifs:
                icon = "white_check_mark" if v.get("verbatim_ok") else "x"
                st.markdown(f":{icon}: `{v.get('match_type', '')}` — offsets [{v.get('relative_start')}, {v.get('relative_end')}]")

        # Show the full parent content with the span highlighted
        st.markdown("---")
        st.markdown("**Full NCERT parent block:**")
        parent_content = parent.get("content", "")
        if span_text and span_text in parent_content:
            highlighted = parent_content.replace(
                span_text,
                f"**:yellow[{span_text}]**"
            )
            st.markdown(highlighted)
        else:
            st.text(parent_content[:2000])

        st.caption(r.get("notes", ""))

    else:
        st.warning(f"Not matched: {cls}")
        st.markdown(f"**Notes:** {r.get('notes', '')}")

        # Show what levels were tried
        levels_tried = r.get("levels_tried", [])
        if levels_tried:
            st.markdown("**Levels tried:**")
            for lt in levels_tried:
                st.caption(f"Level {lt.get('level')}: query='{lt.get('query', '')[:80]}...', parents_tried={lt.get('parents_tried')}")

# ─── Navigation ─────────────────────────────────────────────────────────────

st.divider()
nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
with nav_col1:
    if pyq_idx > 1:
        if st.button("Previous"):
            st.rerun()
with nav_col3:
    if pyq_idx < len(filtered):
        if st.button("Next"):
            st.rerun()

# ─── Raw JSON (collapsible) ─────────────────────────────────────────────────

with st.expander("Raw match JSON"):
    st.json(r)

with st.expander("Raw PYQ JSON"):
    st.json(pyq_data)
