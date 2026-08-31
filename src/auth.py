"""
auth.py
-------
Login gate for MediGuide AI. Every visitor supplies and verifies their
OWN OpenAI API key before the assessment tool becomes available — the
key lives only in st.session_state for that browser session and is
never written to disk or shared across users. This makes the app safe
to deploy publicly without exposing the developer's own key.
"""

import os
import streamlit as st
from openai import OpenAI, AuthenticationError, APIConnectionError

from src.config import APP_NAME
from src.utils import image_to_base64

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


@st.cache_data(show_spinner=False)
def _load_login_images():
    """Cached so the images are base64-encoded only once per app run."""
    return {
        "bg": image_to_base64(os.path.join(ASSETS_DIR, "cross_cardio_bg.jpg")),
        "care_team": image_to_base64(os.path.join(ASSETS_DIR, "care_team.png")),
        "mascot": image_to_base64(os.path.join(ASSETS_DIR, "ai_mascot.png")),
    }


# ---------------------------------------------------------------------
# Styling — split-screen login card with an animated ECG/pulse line
# as the signature visual element (ties directly into the "MediGuide"
# health theme instead of a generic gradient).
# ---------------------------------------------------------------------
def _inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --navy-950: #0A1B2E;
            --navy-900: #10273F;
            --teal-400: #2DD4C4;
            --teal-300: #8DECDF;
            --mist-50: #F5FAF9;
            --slate-600: #44566B;
            --slate-900: #16232E;
            --coral-500: #FF6B5B;
        }

        /* Hide default Streamlit chrome on the login screen */
        [data-testid="stSidebar"], header[data-testid="stHeader"] {
            display: none !important;
        }
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        body, .stApp {
            background: var(--mist-50);
        }

        /* ---- Split screen shell ---- */
        .login-shell {
            display: flex;
            min-height: 100vh;
            width: 100%;
            font-family: 'Inter', sans-serif;
        }
        .login-left {
            flex: 1.1;
            background: radial-gradient(circle at 20% 20%, var(--navy-900), var(--navy-950) 70%);
            background-size: cover;
            background-position: center;
            color: white;
            padding: 4rem 3.5rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            position: relative;
            overflow: hidden;
            min-height: 100vh;
        }
        .care-team-img {
            position: absolute;
            right: -20px;
            bottom: 90px;
            width: 280px;
            opacity: 0.92;
            filter: drop-shadow(0 10px 30px rgba(0,0,0,0.45));
            pointer-events: none;
        }
        .mascot-badge {
            width: 34px;
            height: auto;
            vertical-align: middle;
            margin-right: 0.35rem;
            filter: drop-shadow(0 2px 6px rgba(45, 212, 196, 0.4));
        }
        .login-right {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 3rem 2rem;
        }

        .brand-mark {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 2.5rem;
        }
        .brand-mark svg { width: 30px; height: 30px; }
        .brand-mark span {
            font-family: 'Sora', sans-serif;
            font-weight: 700;
            font-size: 1.15rem;
            letter-spacing: 0.02em;
        }

        .login-left h1 {
            font-family: 'Sora', sans-serif;
            font-weight: 800;
            font-size: 2.6rem;
            line-height: 1.15;
            margin: 0 0 1.1rem 0;
            max-width: 480px;
        }
        .login-left h1 .accent { color: var(--teal-400); }
        .login-left p.sub {
            font-family: 'Inter', sans-serif;
            font-size: 1.02rem;
            color: #B9C6D6;
            max-width: 420px;
            line-height: 1.6;
            margin-bottom: 2.4rem;
        }

        .trust-row {
            display: flex;
            gap: 1.8rem;
            margin-top: 1rem;
        }
        .trust-item {
            font-family: 'Inter', sans-serif;
            font-size: 0.82rem;
            color: #8FA2B8;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .trust-item .dot {
            width: 6px; height: 6px; border-radius: 50%;
            background: var(--teal-400);
            display: inline-block;
        }

        /* ---- ECG pulse line, signature element ---- */
        .pulse-wrap {
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 130px;
            overflow: hidden;
            opacity: 0.9;
        }
        .pulse-wrap svg { width: 200%; height: 100%; }
        .pulse-line {
            fill: none;
            stroke: var(--teal-400);
            stroke-width: 2.2;
            stroke-linecap: round;
            stroke-linejoin: round;
            filter: drop-shadow(0 0 6px rgba(45, 212, 196, 0.55));
            stroke-dasharray: 1600;
            stroke-dashoffset: 0;
            animation: pulse-scroll 7s linear infinite;
        }
        @keyframes pulse-scroll {
            from { transform: translateX(0); }
            to { transform: translateX(-50%); }
        }

        /* ---- Right panel: the login card ---- */
        .login-card {
            width: 100%;
            max-width: 400px;
        }
        .login-card .eyebrow {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--teal-400);
            background: rgba(45, 212, 196, 0.1);
            border: 1px solid rgba(45, 212, 196, 0.35);
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            margin-bottom: 1.1rem;
        }
        .login-card h2 {
            font-family: 'Sora', sans-serif;
            font-weight: 700;
            font-size: 1.55rem;
            color: var(--slate-900);
            margin: 0 0 0.5rem 0;
        }
        .login-card p.desc {
            font-family: 'Inter', sans-serif;
            color: var(--slate-600);
            font-size: 0.92rem;
            line-height: 1.55;
            margin-bottom: 1.6rem;
        }
        .login-card p.desc a { color: var(--teal-400); font-weight: 600; text-decoration: none; }

        /* Streamlit widget re-skin (scoped to the login form) */
        div[data-testid="stForm"] {
            border: none;
            padding: 0;
        }
        div[data-testid="stTextInput"] input {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.85rem !important;
            background: white !important;
            border: 1.5px solid #DCE6E4 !important;
            border-radius: 10px !important;
            padding: 0.7rem 0.9rem !important;
            color: var(--slate-900) !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: var(--teal-400) !important;
            box-shadow: 0 0 0 3px rgba(45, 212, 196, 0.18) !important;
        }
        div[data-testid="stForm"] button {
            width: 100%;
            background: linear-gradient(135deg, var(--teal-400), #21B8AA) !important;
            color: var(--navy-950) !important;
            font-family: 'Sora', sans-serif !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.65rem 0 !important;
            margin-top: 0.6rem;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        div[data-testid="stForm"] button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(45, 212, 196, 0.35);
        }

        .privacy-note {
            font-family: 'Inter', sans-serif;
            font-size: 0.78rem;
            color: #8095A8;
            margin-top: 1.1rem;
            line-height: 1.5;
            display: flex;
            gap: 0.4rem;
        }

        @media (max-width: 900px) {
            .login-shell { flex-direction: column; }
            .login-left { min-height: 42vh; padding: 2.5rem 1.8rem; }
            .login-left h1 { font-size: 1.9rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_left_panel(images: dict):
    bg_style = (
        f"background-image: linear-gradient(135deg, rgba(10,27,46,0.94), "
        f"rgba(10,27,46,0.88) 55%, rgba(16,39,63,0.82)), url('{images['bg']}'); "
        f"background-size: cover; background-position: center;"
        if images.get("bg") else ""
    )
    care_team_html = (
        f'<img class="care-team-img" src="{images["care_team"]}" alt="Care team"/>'
        if images.get("care_team") else ""
    )
    mascot_html = (
        f'<img class="mascot-badge" src="{images["mascot"]}" alt=""/>'
        if images.get("mascot") else ""
    )
    st.markdown(
        f"""
        <div class="login-left" style="{bg_style}">
            <div class="brand-mark">
                {mascot_html}
                <span>{APP_NAME}</span>
            </div>
            <h1>Your <span class="accent">AI-guided</span><br>symptom companion.</h1>
            <p class="sub">
                Connect your own OpenAI API key to unlock structured, safety-first
                guidance — summaries, urgency levels, and next steps, generated
                just for this session.
            </p>
            <div class="trust-row">
                <div class="trust-item"><span class="dot"></span>Key never leaves this session</div>
                <div class="trust-item"><span class="dot"></span>Not medical advice</div>
            </div>
            {care_team_html}
            <div class="pulse-wrap">
                <svg viewBox="0 0 800 130" preserveAspectRatio="none">
                    <path class="pulse-line" d="
                        M0,65 L60,65 L80,65 L95,20 L115,110 L130,65 L180,65
                        L200,65 L215,40 L230,90 L245,65 L400,65
                        L460,65 L480,65 L495,20 L515,110 L530,65 L580,65
                        L600,65 L615,40 L630,90 L645,65 L800,65
                    "/>
                </svg>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def validate_api_key(api_key: str):
    """
    Verifies the key with a lightweight, no-cost call (listing models)
    rather than an actual chat completion. Returns (ok, message).
    """
    if not api_key or not api_key.strip():
        return False, "Please enter your OpenAI API key."

    api_key = api_key.strip()
    if not api_key.startswith("sk-"):
        return False, "That doesn't look like a valid OpenAI key — it should start with 'sk-'."

    try:
        client = OpenAI(api_key=api_key)
        client.models.list()
        return True, "Key verified — welcome in!"
    except AuthenticationError:
        return False, "OpenAI rejected this key. Please double-check and try again."
    except APIConnectionError:
        return False, "Couldn't reach OpenAI to verify the key. Check your internet connection and try again."
    except Exception as e:
        return False, f"Unexpected error while verifying the key: {e}"


def render_login_page():
    """
    Renders the full-screen login experience. On successful verification,
    stores the key in st.session_state and sets authenticated=True.
    Returns nothing — app.py checks st.session_state.authenticated after
    calling this.
    """
    _inject_css()
    images = _load_login_images()

    left, right = st.columns([1.1, 1], gap="small")
    with left:
        _render_left_panel(images)

    with right:
        st.markdown('<div class="login-right"><div class="login-card">', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Get started</span>', unsafe_allow_html=True)
        st.markdown("<h2>Connect your OpenAI key</h2>", unsafe_allow_html=True)
        st.markdown(
            '<p class="desc">Don\'t have one? Create it for free at '
            '<a href="https://platform.openai.com/api-keys" target="_blank">'
            'platform.openai.com/api-keys</a>.</p>',
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            api_key_input = st.text_input(
                "OpenAI API key",
                type="password",
                placeholder="sk-...",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Verify & continue →")

        if submitted:
            with st.spinner("Verifying your key with OpenAI..."):
                ok, message = validate_api_key(api_key_input)
            if ok:
                st.session_state.authenticated = True
                st.session_state.user_api_key = api_key_input.strip()
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        st.markdown(
            '<div class="privacy-note">🔒 Your key is kept only in this browser '
            "session's memory. It is never stored on a server or shared with "
            "anyone else, and is used solely to call OpenAI on your behalf.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div></div>", unsafe_allow_html=True)
