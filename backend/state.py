# state.py
# LangGraph state using TypedDict.
# Each node reads from and writes to this shared state object.

from typing import TypedDict, Optional, List, Annotated
import operator


class AgentState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────
    user_query: str
    dataset_json: str
    dataset_info: str

    # ── Node outputs ────────────────────────────────────────────────────
    intent: str
    plan: List[str]
    code: str
    code_output: str
    chart_html: Optional[str]
    error: Optional[str]
    retry_count: int
    insights: str
    suggestions: Optional[list]
    patterns: Optional[list]

    # ── Conversation memory ─────────────────────────────────────────────
    history: List[dict]

    # ── Routing flag ────────────────────────────────────────────────────
    should_retry: bool

    # ── Step log ────────────────────────────────────────────────────────
    steps_log: List[dict]
