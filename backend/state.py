# state.py
# The AgentState is the single object that flows through every node.
# Each node reads from it and adds its own output to it.
# This is the manual equivalent of LangGraph's TypedDict state.

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class AgentState:
    # ── Input ──────────────────────────────────────────────────────────
    user_query: str = ""          # Raw question from user
    dataset_json: str = ""        # Full dataset serialised to JSON
    dataset_info: str = ""        # Human-readable description for the LLM

    # ── Node outputs (filled as the graph runs) ─────────────────────────
    intent: str = ""              # Parser  → one-sentence summary of the query
    plan: List[str] = field(default_factory=list)  # Planner → ordered steps
    code: str = ""                # CodeGen → Python code to execute
    code_output: str = ""         # Executor → printed output from the code
    chart_html: Optional[str] = None  # Executor → Plotly HTML if chart was made
    error: Optional[str] = None   # Executor → traceback if code failed
    retry_count: int = 0          # How many times we've retried code generation
    insights: str = ""            # Interpreter → plain-English explanation
    suggestions: list = None         # Suggester → follow-up questions
    patterns: list = None            # Detector → proactive anomalies/trends

    # ── Routing flag ────────────────────────────────────────────────────
    should_retry: bool = False    # Set by executor; read by the router

    # ── Step log (streamed to the frontend) ─────────────────────────────
    steps_log: List[dict] = field(default_factory=list)
