from typing import Literal, TypedDict

ActionType = Literal["translate", "summarize"]
LangCode = Literal["ru", "en", "uk", "fr", "es", "de"]


class ConversationTurn(TypedDict):
    role: str
    content: str


class GraphState(TypedDict, total=False):
    # Inputs set by the view before invoking the graph.
    action: ActionType
    message: str
    target_language: LangCode
    conversation: list[ConversationTurn]

    # Derived during traversal.
    source_language: LangCode

    # Outputs — exactly one of these is set on success.
    translation: str
    summary: str

    # Error path — set by _safe wrapper on node failure.
    error: str
    failed_node: str
