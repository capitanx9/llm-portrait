from collections.abc import Callable
from functools import wraps
from typing import Literal, get_args

from django.conf import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from loguru import logger

from .prompts import DETECT_LANG_SYSTEM, SUMMARIZE_SYSTEM, TRANSLATE_SYSTEM
from .state import GraphState, LangCode

# Cap on how many trailing turns we feed into summarize; larger inputs blow up
# Llama3.2:3b's 8k context. No tokenizer pass — just a hard turn cap.
MAX_SUMMARIZE_TURNS = 40

# How many leading characters of the input we send to detect_lang. The model
# needs only a sample to identify the language; sending the full conversation
# would waste a slot of the context window for no benefit.
DETECT_LANG_SAMPLE_CHARS = 500

_VALID_LANG_CODES: frozenset[str] = frozenset(get_args(LangCode))


def _make_llm(temperature: float | None = None) -> ChatOllama:
    return ChatOllama(
        base_url=settings.OLLAMA_URL,
        model=settings.OLLAMA_MODEL,
        temperature=settings.AI_TASK_TEMPERATURE if temperature is None else temperature,
        client_kwargs={"timeout": 600},
    )


def _safe(node: Callable[[GraphState], dict]) -> Callable[[GraphState], dict]:
    """Translate any node exception into structured state.

    LangGraph aborts the run if a node raises; we want graceful degradation
    via fallback_node instead. The wrapper writes error + failed_node so the
    conditional router can route to fallback on the next step.
    """

    @wraps(node)
    def wrapper(state: GraphState) -> dict:
        try:
            return node(state)
        except Exception as exc:
            failed = node.__name__.removesuffix("_node")
            logger.warning("ai_node_failed", node=failed, error=str(exc))
            return {"error": str(exc), "failed_node": failed}

    return wrapper


def _normalise_lang_code(raw: str) -> LangCode:
    cleaned = "".join(c for c in raw.lower() if c.isalpha())[:2]
    if cleaned in _VALID_LANG_CODES:
        return cleaned  # type: ignore[return-value]
    return "en"


def _detect_lang_input_text(state: GraphState) -> str:
    if state.get("action") == "translate":
        return state.get("message", "")
    conversation = state.get("conversation") or []
    joined = "\n".join(f"{turn['role']}: {turn['content']}" for turn in conversation)
    return joined[:DETECT_LANG_SAMPLE_CHARS]


def detect_lang_node(state: GraphState) -> dict:
    text = _detect_lang_input_text(state)
    template = ChatPromptTemplate.from_messages(
        [("system", DETECT_LANG_SYSTEM), ("human", "{text}")]
    )
    response = _make_llm().invoke(template.format_messages(text=text))
    source_language = _normalise_lang_code(str(response.content))
    logger.info("ai_detect_lang", source_language=source_language)
    return {"source_language": source_language}


def translate_node(state: GraphState) -> dict:
    template = ChatPromptTemplate.from_messages(
        [
            ("system", TRANSLATE_SYSTEM),
            ("human", "Target language: {target}\n\nText:\n{message}"),
        ]
    )
    messages = template.format_messages(
        target=state["target_language"],
        message=state["message"],
    )
    response = _make_llm().invoke(messages)
    return {"translation": str(response.content)}


def summarize_node(state: GraphState) -> dict:
    conversation = state.get("conversation") or []
    trimmed = conversation[-MAX_SUMMARIZE_TURNS:]
    joined = "\n".join(f"{turn['role']}: {turn['content']}" for turn in trimmed)
    template = ChatPromptTemplate.from_messages(
        [
            ("system", SUMMARIZE_SYSTEM),
            ("human", "Output language code: {lang}\n\nConversation:\n{conversation}"),
        ]
    )
    messages = template.format_messages(
        lang=state.get("source_language", "en"),
        conversation=joined,
    )
    response = _make_llm().invoke(messages)
    return {"summary": str(response.content)}


def fallback_node(state: GraphState) -> dict:
    return {"error": state.get("error", "unknown error")}


def condition_router(state: GraphState) -> Literal["translate", "summarize", "fallback"]:
    if state.get("error"):
        return "fallback"
    return state["action"]
