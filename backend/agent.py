# agent.py
# LangGraph-powered agent pipeline.
# Each function = one node. The StateGraph wires them together.

import os
import json
import logging
import requests
from typing import Literal
from dotenv import load_dotenv
from langsmith import traceable

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from state import AgentState
from tools import run_code

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

MAX_RETRIES = 3
LLM_TIMEOUT = 30
MAX_OUTPUT_CHARS = 3000
SAFE_LIBRARIES = "pandas, plotly.express, plotly.graph_objects, numpy"

CHART_KEYWORDS = {"chart", "plot", "graph", "visuali", "bar", "line", "scatter", "pie", "histogram", "heatmap", "show me"}

def user_wants_chart(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in CHART_KEYWORDS)


# ── LLM helper ────────────────────────────────────────────────────────────────
@traceable(name="Groq LLM Call")
def call_llm(system: str, user: str, temperature: float = 0.1) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")
    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "temperature": temperature,
            "max_tokens": 1500,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        },
        timeout=LLM_TIMEOUT,
    )
    if resp.status_code == 429:
        raise requests.exceptions.HTTPError(
            "Groq rate limit reached. Please wait a moment and try again.", response=resp
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def extract_code(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        return "\n".join(lines[start:end]).strip()
    return raw


# ── Node 1: Parser ────────────────────────────────────────────────────────────
@traceable(name="1. Query Parser")
def node_parser(state: AgentState) -> AgentState:
    reply = call_llm(
        system=(
            "You are a data analysis query parser. "
            "Given a dataset description and a user question, reply with ONE sentence "
            "describing exactly what analysis the user wants. "
            "Be specific: mention column names, the analysis type, and expected output. "
            "Reply with ONLY that sentence — no preamble, no explanation."
        ),
        user=(
            f"Dataset info:\n{state['dataset_info']}\n\n"
            + (
                "Previous analysis in this session:\n" +
                "\n".join([f"Q: {h['query']}\nA: {h['insights']}" for h in state['history'][-3:]]) +
                "\n\n"
                if state.get('history') else ""
            )
            + f"User question: \"{state['user_query']}\""
        ),
    )
    steps_log = state.get('steps_log', []) + [{"node": "parser", "status": "done", "intent": reply}]
    logger.info(f"Parser → intent: {reply[:100]}")
    return {**state, "intent": reply, "steps_log": steps_log}


# ── Node 2: Planner ───────────────────────────────────────────────────────────
@traceable(name="2. Planner")
def node_planner(state: AgentState) -> AgentState:
    reply = call_llm(
        system=(
            "You are a data analysis planner. "
            "Given a dataset description and an analysis intent, write a numbered list "
            "of 3-5 concrete steps to perform using pandas. "
            "Each step = one short action (e.g. 'Group by category and sum revenue'). "
            "Only include a chart/visualization step if the user explicitly asked for a chart, graph, plot, or visualization. "
            "If no chart was requested, return only data analysis steps with print() output. "
            "Reply ONLY with the numbered list. No other text."
        ),
        user=(
            f"Dataset info:\n{state['dataset_info']}\n\n"
            f"Analysis intent: {state['intent']}"
        ),
    )
    plan = []
    for line in reply.strip().split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            clean = line.split(". ", 1)[-1].lstrip("- ").strip()
            if clean:
                plan.append(clean)
    steps_log = state.get('steps_log', []) + [{"node": "planner", "status": "done", "plan": plan}]
    logger.info(f"Planner → {len(plan)} steps")
    return {**state, "plan": plan, "steps_log": steps_log}


# ── Node 3: Code Generator ────────────────────────────────────────────────────
@traceable(name="3. Code Generator")
def node_codegen(state: AgentState) -> AgentState:
    error_context = ""
    if state.get('error'):
        error_context = (
            f"\n\nYour previous code raised this error:\n{state['error']}\n"
            "Fix it. Try a completely different approach if needed."
        )
    plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(state.get('plan', [])))
    raw = call_llm(
        system=(
            "You are a Python data analyst. Write executable pandas and Plotly code.\n\n"
            "Rules:\n"
            "- Only create a chart if wants_chart is True\n"
            "- If creating a chart, use plotly.express (px) or plotly.graph_objects (go)\n"
            "- The DataFrame is pre-loaded as `df` — do NOT load files\n"
            "- Always assign your figure to a variable named `fig`\n"
            "- Use print() to show numerical results\n"
            "- Always add title and dark theme: fig.update_layout(template='plotly_dark', title='...', xaxis_title='...', yaxis_title='...')\n"
            "- Make charts professional: add color, hover data, and clear labels\n"
            "- Handle NaN/missing values gracefully\n"
            "- Keep printed output concise — avoid printing the entire DataFrame\n"
            "- Reply with ONLY the Python code. No markdown, no explanation."
        ),
        user=(
            f"Dataset info:\n{state['dataset_info']}\n\n"
            f"Plan:\n{plan_text}\n\n"
            f"wants_chart: {user_wants_chart(state['user_query'])}\n"
            f"{error_context}"
        ),
    )
    code = extract_code(raw)
    retry_count = state.get('retry_count', 0)
    steps_log = state.get('steps_log', []) + [{"node": "codegen", "status": "done", "code": code, "retry": retry_count}]
    logger.info(f"CodeGen → {len(code)} chars (retry={retry_count})")
    return {**state, "code": code, "error": None, "steps_log": steps_log}


# ── Node 4: Executor ──────────────────────────────────────────────────────────
@traceable(name="4. Executor")
def node_executor(state: AgentState) -> AgentState:
    import pandas as pd
    import io
    df = pd.read_json(io.StringIO(state['dataset_json']))
    output, chart_html, error = run_code(state['code'], df)

    if error:
        retry_count = state.get('retry_count', 0) + 1
        should_retry = retry_count < MAX_RETRIES
        logger.warning(f"Executor error (retry {retry_count}/{MAX_RETRIES}): {error[:200]}")
        steps_log = state.get('steps_log', []) + [{"node": "executor", "status": "error", "error": error[:400], "retry_count": retry_count}]
        return {**state, "error": error, "retry_count": retry_count, "should_retry": should_retry, "steps_log": steps_log}
    else:
        truncated_output = output[:MAX_OUTPUT_CHARS]
        if len(output) > MAX_OUTPUT_CHARS:
            truncated_output += f"\n... (output truncated at {MAX_OUTPUT_CHARS} chars)"
        logger.info(f"Executor success → output={len(output)} chars, chart={'yes' if chart_html else 'no'}")
        steps_log = state.get('steps_log', []) + [{"node": "executor", "status": "done", "output": truncated_output, "has_chart": chart_html is not None}]
        return {**state, "code_output": truncated_output, "chart_html": chart_html, "error": None, "should_retry": False, "steps_log": steps_log}


# ── Node 5: Interpreter ───────────────────────────────────────────────────────
@traceable(name="5. Interpreter")
def node_interpreter(state: AgentState) -> AgentState:
    reply = call_llm(
        system=(
            "You are a data analyst writing a clear summary for a business user.\n\n"
            "Rules:\n"
            "- Start with the most important finding\n"
            "- Include specific numbers from the output\n"
            "- End with one actionable recommendation if relevant\n"
            "- 2-4 sentences max\n"
            "- Plain English — no jargon, no 'the code shows', no 'the output indicates'"
        ),
        user=(
            f"Original question: \"{state['user_query']}\"\n\n"
            + (
                "Context from earlier in this session:\n" +
                "\n".join([f"Q: {h['query']}\nA: {h['insights']}" for h in state.get('history', [])[-2:]]) +
                "\n\n"
                if state.get('history') else ""
            )
            + f"Code output:\n{state['code_output']}"
        ),
        temperature=0.3,
    )
    steps_log = state.get('steps_log', []) + [{"node": "interpreter", "status": "done", "insights": reply}]
    logger.info("Interpreter → insights generated")
    return {**state, "insights": reply, "steps_log": steps_log}


# ── Node 6: Suggester ─────────────────────────────────────────────────────────
@traceable(name="6. Suggester")
def node_suggester(state: AgentState) -> AgentState:
    reply = call_llm(
        system=(
            "You are a data analyst assistant. Based on the analysis just performed, "
            "suggest exactly 3 short follow-up questions the user could ask next.\n\n"
            "Rules:\n"
            "- Each question must be specific to the dataset columns and findings\n"
            "- Keep each question under 10 words\n"
            "- Make them progressively deeper — surface, then trend, then action\n"
            "- Reply with ONLY a JSON array of 3 strings. Example:\n"
            '  ["Which region has the highest revenue?", "How did sales trend over time?", "Which category has best profit margin?"]\n'
            "- No preamble, no explanation, just the JSON array."
        ),
        user=(
            f"Dataset columns: {state['dataset_info'].splitlines()[0]}\n\n"
            f"Analysis performed: {state['intent']}\n\n"
            f"Key insights: {state['insights']}"
        ),
        temperature=0.4,
    )
    try:
        clean = reply.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        suggestions = json.loads(clean.strip())
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [s for s in suggestions if isinstance(s, str)][:3]
    except Exception:
        suggestions = []
    steps_log = state.get('steps_log', []) + [{"node": "suggester", "status": "done", "suggestions": suggestions}]
    logger.info(f"Suggester → {len(suggestions)} suggestions")
    return {**state, "suggestions": suggestions, "steps_log": steps_log}


# ── Node 7: Pattern Detector ──────────────────────────────────────────────────
@traceable(name="7. Pattern Detector")
def node_detector(state: AgentState) -> AgentState:
    reply = call_llm(
        system=(
            "You are a proactive data analyst. Given a dataset description and recent analysis, "
            "scan for anomalies, unusual patterns, or interesting trends the user did NOT ask about.\n\n"
            "Rules:\n"
            "- Find 1-2 genuinely interesting patterns or anomalies\n"
            "- Each pattern must be specific with actual numbers from the data\n"
            "- Frame each as a short alert with a follow-up question\n"
            "- Only flag things that are genuinely surprising or actionable\n"
            "- If nothing unusual exists, return an empty array\n"
            "- Reply with ONLY a JSON array. Example:\n"
            '  [{"alert": "Revenue dropped 40% in March vs February", "question": "Investigate the March drop?"}]\n'
            "- No preamble, no explanation, just the JSON array."
        ),
        user=(
            f"Dataset info:\n{state['dataset_info']}\n\n"
            f"Analysis performed: {state['intent']}\n\n"
            f"Code output:\n{state['code_output']}\n\n"
            f"Insights: {state['insights']}"
        ),
        temperature=0.2,
    )
    try:
        clean = reply.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        patterns = json.loads(clean.strip())
        if not isinstance(patterns, list):
            patterns = []
        patterns = [p for p in patterns if isinstance(p, dict) and "alert" in p][:2]
    except Exception:
        patterns = []
    steps_log = state.get('steps_log', []) + [{"node": "detector", "status": "done", "patterns": patterns}]
    logger.info(f"Detector → {len(patterns)} patterns found")
    return {**state, "patterns": patterns, "steps_log": steps_log}


# ── Routing function ──────────────────────────────────────────────────────────
def should_retry(state: AgentState) -> Literal["node_codegen", "node_interpreter"]:
    if state.get('error') and state.get('should_retry'):
        return "node_codegen"
    return "node_interpreter"


# ── Build the graph ───────────────────────────────────────────────────────────
def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("node_parser",      node_parser)
    workflow.add_node("node_planner",     node_planner)
    workflow.add_node("node_codegen",     node_codegen)
    workflow.add_node("node_executor",    node_executor)
    workflow.add_node("node_interpreter", node_interpreter)
    workflow.add_node("node_suggester",   node_suggester)
    workflow.add_node("node_detector",    node_detector)

    workflow.set_entry_point("node_parser")
    workflow.add_edge("node_parser",      "node_planner")
    workflow.add_edge("node_planner",     "node_codegen")
    workflow.add_edge("node_codegen",     "node_executor")
    workflow.add_conditional_edges("node_executor", should_retry)
    workflow.add_edge("node_interpreter", "node_suggester")
    workflow.add_edge("node_suggester",   "node_detector")
    workflow.add_edge("node_detector",    END)

    # SqliteSaver persists state so pipeline survives crashes
    import os, sqlite3
    db_path = os.path.join(os.environ.get("TMPDIR", "/tmp"), "agent_checkpoints.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    return workflow.compile(checkpointer=memory)


# ── Graph runner (yields SSE dicts) ──────────────────────────────────────────
def run_graph(user_query: str, dataset_json: str, dataset_info: str, df, history: list = None):
    graph = build_graph()

    initial_state = AgentState(
        user_query=user_query,
        dataset_json=dataset_json,
        dataset_info=dataset_info,
        intent="",
        plan=[],
        code="",
        code_output="",
        chart_html=None,
        error=None,
        retry_count=0,
        insights="",
        suggestions=None,
        patterns=None,
        history=history or [],
        should_retry=False,
        steps_log=[],
    )

    try:
        prev_nodes = set()

        import uuid
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        for chunk in graph.stream(initial_state, config, stream_mode="updates"):
            for node_name, node_state in chunk.items():
                clean_name = node_name.replace("node_", "")

                if clean_name not in prev_nodes:
                    yield {"type": "node_start", "node": clean_name}
                    prev_nodes.add(clean_name)

                if clean_name == "parser":
                    yield {"type": "node_done", "node": "parser", "intent": node_state.get("intent", "")}

                elif clean_name == "planner":
                    yield {"type": "node_done", "node": "planner", "plan": node_state.get("plan", [])}

                elif clean_name == "codegen":
                    yield {"type": "node_done", "node": "codegen", "code": node_state.get("code", ""), "retry": node_state.get("retry_count", 0)}

                elif clean_name == "executor":
                    if node_state.get("error"):
                        retry_count = node_state.get("retry_count", 0)
                        yield {"type": "node_error", "node": "executor", "error": node_state["error"][:400], "retry_count": retry_count}
                        if not node_state.get("should_retry"):
                            yield {"type": "error", "message": f"The agent could not produce working code after {MAX_RETRIES} attempts."}
                            return
                        prev_nodes.discard("codegen")
                    else:
                        yield {
                            "type": "node_done", "node": "executor",
                            "output": node_state.get("code_output", ""),
                            "chart_html": node_state.get("chart_html"),
                        }

                elif clean_name == "interpreter":
                    yield {"type": "node_done", "node": "interpreter", "insights": node_state.get("insights", "")}

                elif clean_name == "suggester":
                    yield {"type": "node_done", "node": "suggester", "suggestions": node_state.get("suggestions", [])}

                elif clean_name == "detector":
                    yield {"type": "node_done", "node": "detector", "patterns": node_state.get("patterns", [])}

        yield {"type": "done"}

    except ValueError as e:
        logger.error(f"Config error: {e}")
        yield {"type": "error", "message": str(e)}

    except requests.exceptions.Timeout:
        logger.error("Groq API timed out")
        yield {"type": "error", "message": "The AI service timed out. Please try again."}

    except requests.exceptions.HTTPError as e:
        logger.error(f"Groq HTTP error: {e}")
        yield {"type": "error", "message": f"AI service error: {str(e)}"}

    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Groq API")
        yield {"type": "error", "message": "Could not connect to the AI service."}

    except Exception as e:
        import traceback
        logger.error(f"Unexpected agent error: {traceback.format_exc()}")
        yield {"type": "error", "message": "An unexpected error occurred. Please try again."}
