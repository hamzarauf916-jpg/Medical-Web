"""
prompts.py
----------
All prompt engineering lives here: the safety system prompt, the
JSON-output schema instructions, a plain PromptTemplate (single string,
used for a simple demo chain), and a ChatPromptTemplate (System + Human
messages, used for the real assessment + streaming narrative).
"""

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# ---------------------------------------------------------------------
# Safety system prompt (shared by every chain that talks to the model)
# ---------------------------------------------------------------------
SYSTEM_SAFETY_RULES = """You are MediGuide AI, an educational medical-information assistant.

Non-negotiable rules you must always follow:
1. You are NOT a doctor and must NEVER present a confirmed diagnosis.
2. Only ever provide general, educational information and *possible*
   explanations, clearly framed as such — never certainties.
3. Always encourage the user to consult a qualified healthcare
   professional for any real diagnosis or treatment.
4. If the symptoms described could indicate a medical emergency
   (e.g. chest pain, difficulty breathing, severe bleeding, stroke
   signs, suicidal ideation), you must set urgency_level to
   "EMERGENCY" and clearly instruct the user to seek immediate
   emergency care.
5. Be calm, clear, and reassuring in tone — avoid causing unnecessary
   alarm, but never minimize genuinely dangerous symptoms.
6. Respond in the language requested by the user (default English).
"""

# JSON schema the model must return (kept as its own string so it can be
# reused by both the structured chain and the narrative chain).
JSON_SCHEMA_INSTRUCTIONS = """Return ONLY a single valid JSON object — no markdown
fences, no commentary, no text before or after it — matching EXACTLY this
structure:

{{
  "summary": "<one paragraph summary of the patient's reported symptoms>",
  "possible_conditions": [
    {{"name": "<possible condition>", "reason": "<why it's plausible, educational only>"}}
  ],
  "urgency_level": "<LOW | MEDIUM | HIGH | EMERGENCY>",
  "recommended_next_steps": ["<step 1>", "<step 2>"],
  "questions_for_doctor": ["<question 1>", "<question 2>"],
  "warning_signs": ["<sign that would require immediate attention>"]
}}
"""

# ---------------------------------------------------------------------
# 1) Plain PromptTemplate — a single reusable string template.
#    Used for a lightweight demo chain / quick single-string calls.
# ---------------------------------------------------------------------
ASSESSMENT_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=[
        "age", "gender", "symptoms", "duration", "severity",
        "existing_conditions", "medications", "notes", "language",
    ],
    template=(
        SYSTEM_SAFETY_RULES
        + "\n\nPatient information:\n"
        + "- Age: {age}\n"
        + "- Gender: {gender}\n"
        + "- Symptoms: {symptoms}\n"
        + "- Duration: {duration}\n"
        + "- Severity (1-10): {severity}\n"
        + "- Existing conditions: {existing_conditions}\n"
        + "- Current medications: {medications}\n"
        + "- Additional notes: {notes}\n"
        + "- Respond in language: {language}\n\n"
        + JSON_SCHEMA_INSTRUCTIONS
    ),
)

# ---------------------------------------------------------------------
# 2) ChatPromptTemplate — System + Human conversation.
#    This is what the LLMChain and the JSON assessment actually use.
# ---------------------------------------------------------------------
ASSESSMENT_CHAT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_SAFETY_RULES + "\n\n" + JSON_SCHEMA_INSTRUCTIONS),
        (
            "human",
            "Patient information:\n"
            "- Age: {age}\n"
            "- Gender: {gender}\n"
            "- Symptoms: {symptoms}\n"
            "- Duration: {duration}\n"
            "- Severity (1-10): {severity}\n"
            "- Existing conditions: {existing_conditions}\n"
            "- Current medications: {medications}\n"
            "- Additional notes: {notes}\n"
            "- Respond in language: {language}\n\n"
            "Please assess this information and return the JSON object now.",
        ),
    ]
)

# ---------------------------------------------------------------------
# 3) Narrative ChatPromptTemplate — used for the streamed, human-readable
#    version of the guidance (no JSON, plain friendly text).
# ---------------------------------------------------------------------
NARRATIVE_CHAT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            SYSTEM_SAFETY_RULES
            + "\n\nWrite a short, warm, easy-to-read narrative (4-6 sentences) "
              "summarising the patient's situation and general guidance. "
              "Do NOT return JSON here — plain natural language only. "
              "End with a reminder to consult a healthcare professional.",
        ),
        (
            "human",
            "Patient information:\n"
            "- Age: {age}\n"
            "- Gender: {gender}\n"
            "- Symptoms: {symptoms}\n"
            "- Duration: {duration}\n"
            "- Severity (1-10): {severity}\n"
            "- Existing conditions: {existing_conditions}\n"
            "- Current medications: {medications}\n"
            "- Additional notes: {notes}\n"
            "- Respond in language: {language}\n",
        ),
    ]
)


def build_raw_message_demo(inputs: dict):
    """
    Demonstrates working directly with SystemMessage / HumanMessage /
    AIMessage objects (a required learning objective), independent of
    the template abstractions above. Returns a list of message objects
    ready to hand to a ChatOpenAI instance.
    """
    return [
        SystemMessage(content=SYSTEM_SAFETY_RULES),
        HumanMessage(
            content=(
                f"Patient is {inputs.get('age')} years old, "
                f"gender: {inputs.get('gender')}, "
                f"reporting: {inputs.get('symptoms')}."
            )
        ),
        # Included purely to demonstrate how an AIMessage slots into a
        # multi-turn conversation history (e.g. a prior assistant turn).
        AIMessage(
            content="Understood. I will keep the safety rules in mind while assessing."
        ),
    ]
