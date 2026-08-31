"""
app.py
------
MediGuide AI — Streamlit front end.
Run with: streamlit run app.py
"""

import os
import streamlit as st

from src.config import (
    APP_NAME, APP_TAGLINE, MEDICAL_DISCLAIMER,
    GENDER_OPTIONS, DURATION_OPTIONS, SYMPTOM_OPTIONS, LANGUAGE_OPTIONS,
    URGENCY_COLORS, DEFAULT_MODEL,
)
from src.cache_manager import apply_cache, CACHE_OPTIONS, CACHE_NONE
from src.chains import run_assessment, stream_narrative
from src.utils import safe_parse_json, validate_assessment_shape, format_symptom_list, normalize_urgency, image_to_base64
from src.auth import render_login_page

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


@st.cache_data(show_spinner=False)
def _load_app_images():
    """Cached so images are base64-encoded only once per app run."""
    return {
        "banner": image_to_base64(os.path.join(ASSETS_DIR, "stethoscope_teal.jpg")),
        "mascot": image_to_base64(os.path.join(ASSETS_DIR, "ai_mascot.png")),
        "medkit": image_to_base64(os.path.join(ASSETS_DIR, "medkit.png")),
        "empty_state": image_to_base64(os.path.join(ASSETS_DIR, "stethoscope_leaves.jpg")),
        "pills": image_to_base64(os.path.join(ASSETS_DIR, "pills.jpg")),
    }


st.set_page_config(page_title=APP_NAME, page_icon="🩺", layout="wide")

# ---------------------------------------------------------------------
# Login gate — every visitor must supply and verify their own OpenAI
# API key before the rest of the app renders. Nothing below this block
# runs until st.session_state.authenticated is True.
# ---------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    render_login_page()
    st.stop()

# ---------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------
if "cache_choice" not in st.session_state:
    st.session_state.cache_choice = CACHE_NONE
if "cache_status" not in st.session_state:
    st.session_state.cache_status = apply_cache(CACHE_NONE)
if "result" not in st.session_state:
    st.session_state.result = None
if "last_inputs" not in st.session_state:
    st.session_state.last_inputs = None
if "history" not in st.session_state:
    st.session_state.history = []  # bonus: session history

images = _load_app_images()

# ---------------------------------------------------------------------
# Shared CSS (consistent with the login page's navy/teal palette)
# ---------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600&display=swap');

    .hero-banner {
        position: relative;
        border-radius: 18px;
        overflow: hidden;
        padding: 2.6rem 2.2rem;
        margin-bottom: 1.6rem;
        min-height: 150px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .hero-banner h1 {
        font-family: 'Sora', sans-serif;
        font-weight: 800;
        font-size: 2rem;
        color: white;
        margin: 0 0 0.4rem 0;
        text-shadow: 0 2px 12px rgba(0,0,0,0.35);
    }
    .hero-banner p {
        font-family: 'Inter', sans-serif;
        color: #E7F6F3;
        font-size: 1rem;
        max-width: 560px;
        margin: 0;
        text-shadow: 0 1px 8px rgba(0,0,0,0.3);
    }
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.2rem;
    }
    .sidebar-brand img { width: 40px; height: auto; }
    .sidebar-brand span {
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        font-size: 1.3rem;
        color: #16232E;
    }
    .results-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-top: 0.4rem;
    }
    .results-header img { width: 36px; height: auto; }
    .results-header h2 {
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        margin: 0;
    }
    .empty-state {
        position: relative;
        border-radius: 16px;
        overflow: hidden;
        padding: 2.4rem 2rem;
        text-align: center;
        margin-top: 1rem;
    }
    .empty-state h3 {
        font-family: 'Sora', sans-serif;
        color: #16232E;
        margin-bottom: 0.4rem;
    }
    .empty-state p {
        font-family: 'Inter', sans-serif;
        color: #44566B;
        max-width: 480px;
        margin: 0 auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-brand">
            <img src="{images['mascot']}" alt=""/>
            <span>{APP_NAME}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(APP_TAGLINE)
    st.warning(MEDICAL_DISCLAIMER)

    st.subheader("⚙️ Model configuration")
    st.text(f"Model: {DEFAULT_MODEL}")
    key_tail = st.session_state.get("user_api_key", "")[-4:]
    st.caption(f"🔑 Connected with key ending in ...{key_tail}")
    if st.button("Log out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pop("user_api_key", None)
        st.session_state.result = None
        st.rerun()

    cache_choice = st.selectbox(
        "Caching backend",
        CACHE_OPTIONS,
        index=CACHE_OPTIONS.index(st.session_state.cache_choice),
        help="InMemoryCache is fastest but resets on restart. "
             "SQLiteCache persists to disk across sessions.",
    )
    if cache_choice != st.session_state.cache_choice:
        st.session_state.cache_choice = cache_choice
        st.session_state.cache_status = apply_cache(cache_choice)
    st.caption(st.session_state.cache_status)

    language = st.selectbox("Answer language", LANGUAGE_OPTIONS, index=0)

    if st.session_state.history:
        with st.expander(f"🕓 Session history ({len(st.session_state.history)})"):
            for i, h in enumerate(reversed(st.session_state.history), 1):
                st.write(f"**{i}.** {h['symptoms']} — urgency: {h['urgency']}")

# ---------------------------------------------------------------------
# Main form
# ---------------------------------------------------------------------
banner_style = (
    f"background-image: linear-gradient(120deg, rgba(10,27,46,0.80), rgba(16,39,63,0.55)), "
    f"url('{images['banner']}'); background-size: cover; background-position: center;"
    if images.get("banner") else "background: linear-gradient(120deg, #10273F, #0A1B2E);"
)
st.markdown(
    f"""
    <div class="hero-banner" style="{banner_style}">
        <h1>{APP_NAME} — Symptom Assessment</h1>
        <p>{APP_TAGLINE}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.info(MEDICAL_DISCLAIMER)

with st.form("assessment_form"):
    col1, col2 = st.columns(2)
    with col1:
        age = st.text_input("Patient age", placeholder="e.g. 29")
        gender = st.selectbox("Gender", GENDER_OPTIONS)
        duration = st.selectbox("Duration of symptoms", DURATION_OPTIONS)
    with col2:
        severity = st.slider("Severity (1 = mild, 10 = severe)", 1, 10, 3)
        symptoms_selected = st.multiselect("Symptoms", SYMPTOM_OPTIONS)
        symptoms_free_text = st.text_input("Other symptoms (optional)", placeholder="e.g. tingling in left arm")

    field_col, img_col = st.columns([3, 1])
    with field_col:
        existing_conditions = st.text_area("Existing medical conditions", placeholder="e.g. asthma, diabetes — or 'none'")
        medications = st.text_area("Current medications", placeholder="e.g. metformin — or 'none'")
    with img_col:
        if images.get("pills"):
            st.image(images["pills"], caption="List anything you currently take", use_container_width=True)

    notes = st.text_area("Additional notes", placeholder="Anything else relevant")

    submitted = st.form_submit_button("Get guidance", use_container_width=True)

# ---------------------------------------------------------------------
# Handle submission
# ---------------------------------------------------------------------
if submitted:
    symptoms_str = format_symptom_list(symptoms_selected, symptoms_free_text)

    if not symptoms_selected and not symptoms_free_text.strip():
        st.warning("⚠️ Please enter at least one symptom before submitting.")
    elif not age.strip():
        st.warning("⚠️ Please enter the patient's age.")
    else:
        inputs = {
            "age": age.strip(),
            "gender": gender,
            "symptoms": symptoms_str,
            "duration": duration,
            "severity": str(severity),
            "existing_conditions": existing_conditions.strip() or "None reported",
            "medications": medications.strip() or "None reported",
            "notes": notes.strip() or "None",
            "language": language,
        }
        st.session_state.last_inputs = inputs

        try:
            with st.spinner("Analysing symptoms..."):
                raw_output = run_assessment(inputs)
                parsed, error = safe_parse_json(raw_output)

            if error or not parsed:
                st.error("⚠️ Something went wrong parsing the AI response.")
                st.write(error)
                with st.expander("Raw model output (for debugging)"):
                    st.code(raw_output)
                st.session_state.result = None
            else:
                missing = validate_assessment_shape(parsed)
                if missing:
                    st.error(f"⚠️ The response was missing expected fields: {', '.join(missing)}")
                    with st.expander("Raw model output (for debugging)"):
                        st.code(raw_output)
                    st.session_state.result = None
                else:
                    parsed["urgency_level"] = normalize_urgency(parsed.get("urgency_level"))
                    st.session_state.result = parsed
                    st.session_state.history.append(
                        {"symptoms": symptoms_str, "urgency": parsed["urgency_level"]}
                    )
        except RuntimeError as e:
            st.error(f"⚠️ Configuration error: {e}")
        except Exception as e:
            st.error(f"⚠️ Unexpected error calling the AI model: {e}")

if not st.session_state.result:
    empty_style = (
        f"background-image: linear-gradient(180deg, rgba(255,255,255,0.55), rgba(255,255,255,0.55)), "
        f"url('{images['empty_state']}'); background-size: cover; background-position: center;"
        if images.get("empty_state") else "background: #F5FAF9;"
    )
    st.markdown(
        f"""
        <div class="empty-state" style="{empty_style}">
            <h3>No guidance generated yet</h3>
            <p>Fill in the details above and press <b>Get guidance</b> to receive a
            structured, AI-generated symptom summary, urgency level, and next steps.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# Results dashboard
# ---------------------------------------------------------------------
if st.session_state.result:
    result = st.session_state.result
    inputs = st.session_state.last_inputs
    urgency = result.get("urgency_level", "MEDIUM")

    st.divider()
    st.markdown(
        f"""
        <div class="results-header">
            <img src="{images['medkit']}" alt=""/>
            <h2>Results</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Urgency level", urgency)
    m2.metric("Severity reported", f"{inputs['severity']}/10")
    m3.metric("Duration", inputs["duration"])

    banner_kind = URGENCY_COLORS.get(urgency, "info")
    banner_text = {
        "LOW": "✅ Low urgency — general self-care and monitoring is likely appropriate.",
        "MEDIUM": "ℹ️ Medium urgency — consider seeing a healthcare professional soon.",
        "HIGH": "⚠️ High urgency — please see a healthcare professional promptly.",
        "EMERGENCY": "🚨 EMERGENCY — seek immediate emergency medical help now.",
    }.get(urgency, "")
    getattr(st, banner_kind)(banner_text)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Summary & Narrative", "Possible Conditions", "Next Steps & Questions", "Warning Signs"]
    )

    with tab1:
        st.subheader("Patient symptom summary")
        st.write(result.get("summary", ""))

        st.subheader("AI-generated narrative")
        if st.button("🔊 Stream narrative explanation"):
            st.write_stream(stream_narrative(inputs))

    with tab2:
        st.subheader("Possible conditions (for education only)")
        conditions = result.get("possible_conditions", [])
        if conditions:
            for c in conditions:
                with st.expander(c.get("name", "Unnamed condition")):
                    st.write(c.get("reason", ""))
        else:
            st.write("No specific conditions suggested.")
        st.caption("These are general educational possibilities, not a diagnosis.")

    with tab3:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("✅ Recommended next steps")
            for step in result.get("recommended_next_steps", []):
                st.write(f"- {step}")
        with col_b:
            st.subheader("❓ Questions for your doctor")
            for q in result.get("questions_for_doctor", []):
                st.write(f"- {q}")

    with tab4:
        st.subheader("🚩 Warning signs requiring immediate attention")
        for w in result.get("warning_signs", []):
            st.error(w)
        if not result.get("warning_signs"):
            st.write("None specifically flagged — still seek care if symptoms worsen.")

    st.success(MEDICAL_DISCLAIMER)
