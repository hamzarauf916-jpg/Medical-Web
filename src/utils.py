"""
utils.py
--------
Small stateless helpers: safe JSON parsing (never lets a malformed
model response crash the app), image encoding for custom UI, and a
couple of formatting utilities.
"""

import json
import re
import base64
from pathlib import Path


def image_to_base64(path: str) -> str:
    """
    Reads a local image file and returns a data URI string suitable for
    use in CSS (background-image: url(...)) or an <img src="..."> tag.
    Returns an empty string if the file can't be found, so callers can
    fail gracefully instead of crashing the page.
    """
    try:
        file_path = Path(path)
        data = file_path.read_bytes()
        ext = file_path.suffix.lstrip(".").lower()
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:image/{mime};base64,{encoded}"
    except Exception:
        return ""


def strip_json_fences(text: str) -> str:
    """
    Removes accidental ```json ... ``` fences or stray leading/trailing
    text the model sometimes adds despite instructions.
    """
    if not text:
        return text
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ``` fences.
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def safe_parse_json(raw_text: str):
    """
    Attempts to parse the model's raw text output as JSON.

    Returns a tuple: (parsed_dict_or_None, error_message_or_None)
    Never raises — callers should check which element is None.
    """
    if not raw_text or not raw_text.strip():
        return None, "The model returned an empty response."

    cleaned = strip_json_fences(raw_text)

    try:
        parsed = json.loads(cleaned)
        return parsed, None
    except json.JSONDecodeError as e:
        return None, f"Could not parse the model's JSON response ({e})."


REQUIRED_KEYS = [
    "summary",
    "possible_conditions",
    "urgency_level",
    "recommended_next_steps",
    "questions_for_doctor",
    "warning_signs",
]


def validate_assessment_shape(parsed: dict):
    """
    Checks that all required keys are present. Returns a list of any
    missing keys (empty list = valid shape).
    """
    if not isinstance(parsed, dict):
        return REQUIRED_KEYS
    return [k for k in REQUIRED_KEYS if k not in parsed]


def format_symptom_list(selected_symptoms: list, free_text: str) -> str:
    """
    Combines the multiselect symptom list with any free-text symptoms
    into one clean comma-separated string for the prompt.
    """
    items = list(selected_symptoms) if selected_symptoms else []
    if free_text and free_text.strip():
        items.append(free_text.strip())
    return ", ".join(items) if items else "None reported"


def normalize_urgency(level: str) -> str:
    """
    Normalizes the urgency level string to one of the four expected
    buckets, defaulting to MEDIUM if the model returns something
    unexpected (fail-safe rather than crashing the UI).
    """
    if not level:
        return "MEDIUM"
    level = level.strip().upper()
    return level if level in ("LOW", "MEDIUM", "HIGH", "EMERGENCY") else "MEDIUM"
