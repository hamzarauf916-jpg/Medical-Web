"""
chains.py
---------
Builds the ChatOpenAI model, the reusable LLMChain for structured
assessment, and a generator function for streaming the narrative
version of the guidance.
"""

import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain

from src.config import OPENAI_API_KEY, DEFAULT_MODEL, DEFAULT_TEMPERATURE
from src.prompts import ASSESSMENT_CHAT_TEMPLATE, NARRATIVE_CHAT_TEMPLATE


def get_active_api_key() -> str:
    """
    Resolves which API key to use: the key the user entered on the
    login page (st.session_state) takes priority, since this is a
    publicly deployable app where each visitor brings their own key.
    Falls back to a .env-configured key only for local development.
    """
    return st.session_state.get("user_api_key") or OPENAI_API_KEY


def get_llm(temperature: float = DEFAULT_TEMPERATURE, streaming: bool = False) -> ChatOpenAI:
    """
    Creates a ChatOpenAI instance. Caching (if enabled via
    cache_manager.set_cache) is applied automatically by LangChain's
    global cache registry — no extra wiring needed here.
    """
    api_key = get_active_api_key()
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key found. Please log in again with a valid key."
        )
    return ChatOpenAI(
        model=DEFAULT_MODEL,
        temperature=temperature,
        api_key=api_key,
        streaming=streaming,
    )


def build_assessment_chain() -> LLMChain:
    """
    The core reusable LLMChain: combines the ChatPromptTemplate with the
    LLM to produce the structured JSON assessment.
    """
    llm = get_llm(streaming=False)
    return LLMChain(llm=llm, prompt=ASSESSMENT_CHAT_TEMPLATE)


def run_assessment(inputs: dict) -> str:
    """
    Runs the assessment chain and returns the raw text response
    (expected to be a JSON string — see utils.safe_parse_json).
    """
    chain = build_assessment_chain()
    result = chain.invoke(inputs)
    # LLMChain.invoke returns a dict; the text lives under the output key.
    return result.get("text", "") if isinstance(result, dict) else str(result)


def stream_narrative(inputs: dict):
    """
    Generator that yields chunks of the human-readable narrative as the
    model produces them, for use with st.write_stream() in the UI.
    """
    llm = get_llm(streaming=True)
    messages = NARRATIVE_CHAT_TEMPLATE.format_messages(**inputs)
    for chunk in llm.stream(messages):
        if chunk.content:
            yield chunk.content
