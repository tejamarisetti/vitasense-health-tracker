"""
VitaSense AI - Assistant Intent Router and Contextual Answering Engine
POST /api/assistant implementation complying strictly with docs/ASSISTANT_SPEC.md

Rules:
1. Intent routing with LLM / safe classifier.
2. Greetings/small talk -> plain conversational reply ("Hi! How can I help you?"). No cards!
3. Data questions -> answer ONLY from values passed in context, else "I don't have that data".
4. Never diagnose; politely refuse with standard medical disclaimer.
5. Label all data as demonstration/replay data ("REPLAY: public dataset, not live").
6. Out-of-scope -> polite redirect.
7. Cards/portfolio-style UI blocks render ONLY when user explicitly asks to see data, never as fallback.
"""

import os
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env if present
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


class AssistantContext(BaseModel):
    latest_reading: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    source: Optional[str] = "PPG-DaLiA (REPLAY: public dataset, not live)"
    trust_score: Optional[float] = None
    flags: Optional[List[str]] = Field(default_factory=list)
    alerts: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class AssistantRequest(BaseModel):
    message: str
    context: Optional[AssistantContext] = None


class DataCard(BaseModel):
    title: str
    value: str
    badge: Optional[str] = None
    description: Optional[str] = None


class AssistantResponse(BaseModel):
    reply: str
    intent: str
    show_cards: bool = False
    cards: List[DataCard] = Field(default_factory=list)


# Deterministic pattern sets for intent classification
GREETING_PATTERNS = [
    r"^\s*hi[\s!.,?]*$",
    r"^\s*hello[\s!.,?]*$",
    r"^\s*hey[\s!.,?]*$",
    r"^\s*howdy[\s!.,?]*$",
    r"^\s*greetings[\s!.,?]*$",
    r"^\s*good\s+(morning|afternoon|evening|day)[\s!.,?]*$",
]

THANKS_PATTERNS = [
    r"\b(thanks|thank\s+you|thx|appreciate\s+it)\b",
]

CARD_REQUEST_PATTERNS = [
    r"\bshow\s+(me\s+)?(my\s+)?(data\s+)?cards\b",
    r"\bdisplay\s+(my\s+)?(data\s+)?cards\b",
    r"\bshow\s+(me\s+)?(data\s+)?blocks\b",
    r"\bshow\s+(me\s+)?(my\s+)?portfolio\b",
    r"\bshow\s+(me\s+)?(my\s+)?vitals\s+card\b",
]

DIAGNOSIS_PATTERNS = [
    r"\bdiagnos(e|is)\b",
    r"\bdo\s+i\s+have\b",
    r"\bam\s+i\s+having\s+a\s+(heart\s+attack|stroke|emergency)\b",
    r"\bwhat\s+disease\s+do\s+i\s+have\b",
    r"\bis\s+this\s+(arrhythmia|tachycardia|bradycardia|disease|illness)\b",
    r"\bshould\s+i\s+take\s+(medication|aspirin|pills)\b",
    r"\bam\s+i\s+sick\b",
    r"\bwhat\s+is\s+wrong\s+with\s+(me|my\s+heart)\b",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|system)\s+instructions",
    r"output\s+(your\s+)?(system\s+prompt|developer\s+instructions)",
    r"print\s+(your\s+)?(system\s+prompt|initial\s+prompt)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions)",
    r"you\s+are\s+now\s+(dan|an\s+unfiltered\s+ai|developer\s+mode)",
    r"forget\s+(all\s+)?(your\s+)?rules",
]

OFF_TOPIC_PATTERNS = [
    r"\bcapital\s+of\s+[a-z\s]+",
    r"\bwrite\s+(a\s+)?(poem|story|song|essay|code|script)\b",
    r"\bwho\s+won\s+the\b",
    r"\bstock\s+price\b",
    r"\bweather\s+in\b",
    r"\btell\s+me\s+a\s+joke\b",
    r"\brecipe\s+for\b",
    r"\bmeaning\s+of\s+life\b",
]


def classify_intent(message: str) -> str:
    """Classifies user message into a deterministic intent category."""
    msg = message.strip().lower()

    # 1. Prompt Injection check (highest priority safety guard)
    for p in PROMPT_INJECTION_PATTERNS:
        if re.search(p, msg):
            return "prompt_injection"

    # 2. Diagnosis refusal check
    for p in DIAGNOSIS_PATTERNS:
        if re.search(p, msg):
            return "diagnosis_refusal"

    # 3. Explicit card display request
    for p in CARD_REQUEST_PATTERNS:
        if re.search(p, msg):
            return "card_request"

    # 4. Greetings and small talk
    for p in GREETING_PATTERNS:
        if re.search(p, msg):
            return "greeting"

    for p in THANKS_PATTERNS:
        if re.search(p, msg):
            return "thanks"

    # 5. Off topic queries
    for p in OFF_TOPIC_PATTERNS:
        if re.search(p, msg):
            return "off_topic"

    # Default to data inquiry or general telemetry question
    return "data_inquiry"


def build_cards_from_context(ctx: Optional[AssistantContext]) -> List[DataCard]:
    """Generates structured cards only when user explicitly asks for cards."""
    if not ctx:
        return []

    cards = []
    if ctx.latest_reading:
        hr_val = ctx.latest_reading.get("hr", "N/A")
        unit = ctx.latest_reading.get("unit", "bpm")
        cards.append(DataCard(
            title="Heart Rate",
            value=f"{hr_val} {unit}",
            badge="Replay",
            description=f"Source: {ctx.source or 'PPG-DaLiA'}"
        ))

    if ctx.trust_score is not None:
        pct = int(round(ctx.trust_score * 100))
        label = "High Integrity" if pct >= 70 else "Low Trust / Motion"
        cards.append(DataCard(
            title="Trust Score",
            value=f"{pct}%",
            badge=label,
            description="Rule-based signal quality index"
        ))

    if ctx.flags:
        cards.append(DataCard(
            title="Active Flags",
            value=", ".join(ctx.flags),
            badge="Telemetry",
            description="Software validation checks"
        ))

    if ctx.alerts:
        cards.append(DataCard(
            title="Alert State",
            value=f"{len(ctx.alerts)} Active Alert(s)",
            badge="Alert Engine",
            description="Tachycardia threshold check"
        ))

    return cards


def query_gemini_llm(user_message: str, ctx: AssistantContext) -> Optional[str]:
    """
    Attempts to query Gemini API if GEMINI_API_KEY is configured in .env.
    Injects context and strictly enforces system instructions.
    Returns generated text or None if error/unavailable.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VITASENSE_LLM_API_KEY")
    if not api_key or not api_key.strip():
        return None

    # Context representation
    context_str = (
        f"Source: {ctx.source}\n"
        f"Timestamp: {ctx.timestamp}\n"
        f"Latest Reading: {ctx.latest_reading}\n"
        f"Trust Score: {ctx.trust_score}\n"
        f"Flags: {ctx.flags}\n"
        f"Alerts: {ctx.alerts}\n"
    )

    system_instruction = (
        "You are VitaSense Assistant, an educational and research AI for wearable physiological telemetry.\n"
        "STRICT SAFETY & PRIVACY RULES:\n"
        "1. Answer ONLY using the facts present in the provided Telemetry Context. If asked about a vital or metric not in context, reply 'I don't have that data.'\n"
        "2. NEVER provide clinical diagnoses, medical advice, or prescribe medications.\n"
        "3. Always label data as replay or demonstration data ('REPLAY: public dataset, not live').\n"
        "4. Do NOT output markdown card containers or visual blocks.\n"
        "5. Keep responses concise, objective, and polite.\n"
    )

    prompt = f"{system_instruction}\nTelemetry Context:\n{context_str}\n\nUser Question: {user_message}"

    candidate_models = ["gemini-robotics-er-2-preview", "gemini-flash-latest", "gemini-2.5-flash"]
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            import httpx
            resp = httpx.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except Exception:
            continue

    return None


def process_assistant_message(req: AssistantRequest) -> AssistantResponse:
    """
    Main entry point for POST /api/assistant.
    Strictly follows guidelines:
    - Greetings -> plain conversational reply. NO cards.
    - Data inquiry -> answers only from values passed in context, else "I don't have that data".
    - Never diagnose.
    - Label demo/replay data.
    - Out of scope -> polite redirect.
    - Prompt injection -> refuse safely.
    - Cards -> render ONLY on explicit request, never as fallback.
    """
    intent = classify_intent(req.message)
    ctx = req.context or AssistantContext()
    source_label = ctx.source or "PPG-DaLiA (REPLAY: public dataset, not live)"

    if intent == "prompt_injection":
        return AssistantResponse(
            reply="I cannot disregard my guidelines, reveal system prompts, or simulate unconstrained modes. I am VitaSense Assistant, dedicated solely to explaining wearable telemetry and signal quality metrics.",
            intent="prompt_injection",
            show_cards=False,
            cards=[],
        )

    if intent == "diagnosis_refusal":
        return AssistantResponse(
            reply="I cannot provide medical diagnoses or clinical advice. VitaSense is an educational and research tool; please consult a qualified healthcare professional.",
            intent="diagnosis_refusal",
            show_cards=False,
            cards=[],
        )

    if intent == "greeting":
        return AssistantResponse(
            reply="Hi! How can I help you?",
            intent="greeting",
            show_cards=False,
            cards=[],
        )

    if intent == "thanks":
        return AssistantResponse(
            reply="You're welcome! Let me know if you have any questions about your health tracking data or signal validation.",
            intent="thanks",
            show_cards=False,
            cards=[],
        )

    if intent == "off_topic":
        return AssistantResponse(
            reply="I specialize in health monitoring telemetry and data quality. I can't help with questions outside your health tracking data.",
            intent="off_topic",
            show_cards=False,
            cards=[],
        )

    if intent == "card_request":
        cards = build_cards_from_context(ctx)
        reply_text = (
            f"Here are your telemetry cards from {source_label}:"
            if cards
            else "I don't have enough telemetry data in your current context to generate cards."
        )
        return AssistantResponse(
            reply=reply_text,
            intent="card_request",
            show_cards=bool(cards),
            cards=cards,
        )

    # intent == "data_inquiry"
    # 1. Try Gemini LLM if API key is present
    gemini_reply = query_gemini_llm(req.message, ctx)
    if gemini_reply:
        return AssistantResponse(
            reply=gemini_reply,
            intent="data_inquiry",
            show_cards=False,
            cards=[],
        )

    # 2. Deterministic rule-based engine fallback (docs/ASSISTANT_SPEC.md)
    msg_lower = req.message.lower()

    # Check for specific metrics requested
    wants_hr = any(k in msg_lower for k in ["heart rate", "hr", "pulse", "reading", "bpm", "vitals"])
    wants_trust = any(k in msg_lower for k in ["trust", "quality", "score", "sqi", "confidence"])
    wants_time = any(k in msg_lower for k in ["time", "when", "timestamp", "date"])
    wants_source = any(k in msg_lower for k in ["source", "where", "origin", "dataset"])
    wants_flags = any(k in msg_lower for k in ["flag", "artifact", "noise", "motion"])
    wants_alerts = any(k in msg_lower for k in ["alert", "alarm", "tachycardia"])

    # Unsupported or missing metrics (e.g., blood pressure, glucose, temperature)
    unsupported_metrics = ["blood pressure", "bp", "glucose", "sugar", "temperature", "temp", "spo2", "oxygen", "weight", "sleep"]
    if any(m in msg_lower for m in unsupported_metrics):
        return AssistantResponse(
            reply="I don't have that data. My available telemetry context currently includes wrist-PPG heart rate, rule-based trust score, and motion flags from replay recordings.",
            intent="data_inquiry",
            show_cards=False,
            cards=[],
        )

    parts = []
    has_any_data = False

    if wants_hr or (not wants_trust and not wants_time and not wants_flags and not wants_alerts):
        if ctx.latest_reading and "hr" in ctx.latest_reading:
            hr_val = ctx.latest_reading["hr"]
            unit = ctx.latest_reading.get("unit", "bpm")
            parts.append(f"latest heart rate is {hr_val} {unit}")
            has_any_data = True
        elif wants_hr:
            return AssistantResponse(
                reply="I don't have that data in your current context.",
                intent="data_inquiry",
                show_cards=False,
                cards=[],
            )

    if wants_trust:
        if ctx.trust_score is not None:
            pct = int(round(ctx.trust_score * 100))
            parts.append(f"trust score is {pct}% (signal quality: {ctx.trust_score:.2f})")
            has_any_data = True
        else:
            return AssistantResponse(
                reply="I don't have that data in your current context.",
                intent="data_inquiry",
                show_cards=False,
                cards=[],
            )

    if wants_time:
        if ctx.timestamp:
            parts.append(f"recorded at {ctx.timestamp}")
            has_any_data = True
        else:
            return AssistantResponse(
                reply="I don't have that data in your current context.",
                intent="data_inquiry",
                show_cards=False,
                cards=[],
            )

    if wants_flags:
        if ctx.flags is not None:
            if ctx.flags:
                parts.append(f"active flags: {', '.join(ctx.flags)}")
            else:
                parts.append("no artifact flags detected")
            has_any_data = True

    if wants_alerts:
        if ctx.alerts is not None:
            if ctx.alerts:
                parts.append(f"{len(ctx.alerts)} active alert(s)")
            else:
                parts.append("no active alerts")
            has_any_data = True

    if not has_any_data:
        return AssistantResponse(
            reply="I don't have that data. You can ask about your latest heart rate, trust score, timestamp, or signal validation flags.",
            intent="data_inquiry",
            show_cards=False,
            cards=[],
        )

    # Compose response citing values and demo/replay disclaimer
    details = "; ".join(parts)
    reply_msg = f"According to your current context ({source_label}), your {details}. (Notice: Replay/demonstration data, not live sensor readings)."

    return AssistantResponse(
        reply=reply_msg,
        intent="data_inquiry",
        show_cards=False,
        cards=[],
    )
