"""
config.py
---------
Loads environment variables (API key, model settings) and centralizes
all the static options used to build the Streamlit form (dropdowns,
sliders, etc). Keeping these in one place makes the UI code in app.py
much easier to read.
"""

import os
from dotenv import load_dotenv

# Load variables from .env into the process environment.
# This must run before anything tries to read OPENAI_API_KEY.
load_dotenv()

# ---------------------------------------------------------------------
# API / model settings
# ---------------------------------------------------------------------
# NOTE: This is only a fallback for local development/testing.
# In normal use, each visitor enters and verifies their own key on the
# login page (see src/auth.py) — that key is what actually gets used.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

# Where the SQLite cache file will live.
SQLITE_CACHE_PATH = os.getenv("SQLITE_CACHE_PATH", ".cache/mediguide_cache.db")

APP_NAME = "MediGuide AI"
APP_TAGLINE = "Educational AI symptom guidance assistant — not a substitute for a doctor."

# ---------------------------------------------------------------------
# Form options
# ---------------------------------------------------------------------
GENDER_OPTIONS = ["Female", "Male", "Non-binary", "Prefer not to say"]

DURATION_OPTIONS = [
    "Less than 24 hours",
    "1-3 days",
    "4-7 days",
    "1-2 weeks",
    "2-4 weeks",
    "More than a month",
]

SYMPTOM_OPTIONS = [
    "Fever", "Cough", "Sore throat", "Runny nose", "Headache",
    "Fatigue", "Nausea", "Vomiting", "Diarrhea", "Abdominal pain",
    "Chest pain", "Shortness of breath", "Dizziness", "Rash",
    "Joint pain", "Muscle aches", "Loss of appetite", "Sore eyes",
    "Ear pain", "Back pain",
]

LANGUAGE_OPTIONS = ["English", "Urdu", "Spanish", "French", "Arabic"]

URGENCY_COLORS = {
    "LOW": "success",
    "MEDIUM": "info",
    "HIGH": "warning",
    "EMERGENCY": "error",
}

MEDICAL_DISCLAIMER = (
    "⚠️ **Medical Disclaimer:** MediGuide AI is an educational prototype only. "
    "It is **not** a licensed doctor, does not provide a medical diagnosis, and "
    "cannot replace professional medical advice. If this is a medical emergency, "
    "call your local emergency number immediately."
)
