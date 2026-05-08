from typing import Any

from langgraph.graph import END, StateGraph

from .nodes import (
    _safe,
    condition_router,
    detect_lang_node,
    fallback_node,
    summarize_node,
    translate_node,
)
from .state import GraphState


def build_graph() -> Any:
    g: StateGraph = StateGraph(GraphState)
    g.add_node("detect_lang", _safe(detect_lang_node))
    g.add_node("translate", _safe(translate_node))
    g.add_node("summarize", _safe(summarize_node))
    g.add_node("fallback", fallback_node)

    g.set_entry_point("detect_lang")
    g.add_conditional_edges(
        "detect_lang",
        condition_router,
        {"translate": "translate", "summarize": "summarize", "fallback": "fallback"},
    )
    g.add_conditional_edges(
        "translate",
        lambda s: "fallback" if s.get("error") else END,
        {"fallback": "fallback", END: END},
    )
    g.add_conditional_edges(
        "summarize",
        lambda s: "fallback" if s.get("error") else END,
        {"fallback": "fallback", END: END},
    )
    g.add_edge("fallback", END)
    return g.compile()


# Module-level singleton: building the graph allocates state-machine internals
# we don't want to repeat per request. Tests patch ChatOllama at the node level,
# so the singleton doesn't hurt isolation.
GRAPH = build_graph()


def run_graph(payload: dict) -> dict:
    return dict(GRAPH.invoke(payload))
