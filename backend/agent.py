# agent.py
# A hand-rolled LangGraph-style agent pipeline.
# Each function = one node. The graph() generator runs them in order,
# yielding SSE-ready dicts after each node so Flask can stream them live.

import os
import json
import requests
from dotenv import load_dotenv

from state import AgentState
from tools import run_code

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


# ── LLM helper ────────────────────────────────────────────────────────────────

def call_llm(system: str, user: str, temperature: float = 0.1) -> str:
    """
    Call Groq's OpenAI-compatible endpoint.
    Raises on HTTP error so the executor can catch and handle it.
    """
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
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def extract_code(raw: str) -> str:
    """Strip markdown code fences if the LLM wrapped the code in them."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        return "\n".join(lines[start:end]).strip()
    return raw


# ── Node 1: Parser ────────────────────────────────────────────────────────────

def node_parser(state: AgentState) -> AgentState:
    """
    Understand what the user is asking for.
    Output: one-sentence intent description.
    """
    reply = call_llm(
        system=(
            "You are a data analysis query parser. "
            "Given a dataset description and a user question, reply with ONE sentence "
            "describing exactly what analysis the user wants. "
            "Be specific: mention column names, the analysis type, and expected output. "
            "Reply with ONLY that sentence — no preamble, no explanation."
        ),
        user=(
            f"Dataset info:\n{state.dataset_info}\n\n"
            f'User question: "{state.user_query}"'
        ),
    )
    state.intent = reply
    state.steps_log.append({"node": "parser", "status": "done", "intent": reply})
    return state


# ── Node 2: Planner ───────────────────────────────────────────────────────────

def node_planner(state: AgentState) -> AgentState:
    """
    Break the analysis into 3-5 ordered steps.
    Output: list of step strings.
    """
    reply = call_llm(
        system=(
            "You are a data analysis planner. "
            "Given a dataset description and an analysis intent, write a numbered list "
            "of 3-5 concrete steps to perform using pandas. "
            "Each step = one short action (e.g. 'Group by category and sum revenue'). "
            "Reply ONLY with the numbered list. No other text."
        ),
        user=(
            f"Dataset info:\n{state.dataset_info}\n\n"
            f"Analysis intent: {state.intent}"
        ),
    )

    plan = []
    for line in reply.strip().split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            clean = line.split(". ", 1)[-1].lstrip("- ").strip()
            if clean:
                plan.append(clean)

    state.plan = plan
    state.steps_log.append({"node": "planner", "status": "done", "plan": plan})
    return state


# ── Node 3: Code Generator ────────────────────────────────────────────────────

def node_codegen(state: AgentState) -> AgentState:
    """
    Write executable Python code for the analysis.
    On retries, the previous error is included so the LLM can fix it.
    """
    error_context = ""
    if state.error:
        error_context = (
            f"\n\nYour previous code raised this error:\n{state.error}\n"
            "Fix it. Try a completely different approach if needed."
        )

    plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(state.plan))

    raw = call_llm(
        system=(
            "You are a Python data analyst. Write executable pandas/matplotlib code.\n\n"
            "Rules:\n"
            "- The DataFrame is pre-loaded as `df` — do NOT load files\n"
            "- Use print() to show results\n"
            "- For charts: use plt.style.use('dark_background') for dark theme, "
            "  do NOT call plt.show() — just build the figure\n"
            "- Add chart titles and axis labels\n"
            "- Handle NaN/missing values gracefully\n"
            "- Reply with ONLY the Python code. No markdown, no explanation."
        ),
        user=(
            f"Dataset info:\n{state.dataset_info}\n\n"
            f"Plan:\n{plan_text}"
            f"{error_context}"
        ),
    )

    state.code = extract_code(raw)
    state.error = None  # Clear previous error
    state.steps_log.append({
        "node": "codegen",
        "status": "done",
        "code": state.code,
        "retry": state.retry_count,
    })
    return state


# ── Node 4: Executor ──────────────────────────────────────────────────────────

def node_executor(state: AgentState, df) -> AgentState:
    """
    Run the generated code.
    If it fails and we haven't hit the retry limit, sets should_retry=True
    which sends the pipeline back to node_codegen.
    """
    output, chart_b64, error = run_code(state.code, df)

    if error:
        state.error = error
        state.retry_count += 1
        state.should_retry = state.retry_count < 3
        state.steps_log.append({
            "node": "executor",
            "status": "error",
            "error": error[:400],
            "retry_count": state.retry_count,
        })
    else:
        state.code_output = output
        state.chart_b64 = chart_b64
        state.error = None
        state.should_retry = False
        state.steps_log.append({
            "node": "executor",
            "status": "done",
            "output": output,
            "has_chart": chart_b64 is not None,
        })

    return state


# ── Node 5: Interpreter ───────────────────────────────────────────────────────

def node_interpreter(state: AgentState) -> AgentState:
    """
    Read the code output and write plain-English insights.
    This is what the user actually reads.
    """
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
            f'Original question: "{state.user_query}"\n\n'
            f"Code output:\n{state.code_output}"
        ),
        temperature=0.3,
    )
    state.insights = reply
    state.steps_log.append({"node": "interpreter", "status": "done", "insights": reply})
    return state


# ── Graph runner (yields SSE dicts) ──────────────────────────────────────────

def run_graph(user_query: str, dataset_json: str, dataset_info: str, df):
    """
    Execute the full agent pipeline, yielding one dict per event.
    Flask's SSE route iterates this and sends each dict as `data: {...}\\n\\n`.

    Flow:
        parser → planner → codegen → executor
                                ↑         │ error & retry_count < 3
                                └─────────┘
                            executor (success) → interpreter → done
    """
    import pandas as pd

    state = AgentState(
        user_query=user_query,
        dataset_json=dataset_json,
        dataset_info=dataset_info,
    )

    try:
        # ── Parser ──────────────────────────────────────────────────────
        yield {"type": "node_start", "node": "parser"}
        state = node_parser(state)
        yield {"type": "node_done", "node": "parser", "intent": state.intent}

        # ── Planner ─────────────────────────────────────────────────────
        yield {"type": "node_start", "node": "planner"}
        state = node_planner(state)
        yield {"type": "node_done", "node": "planner", "plan": state.plan}

        # ── CodeGen + Executor (with retry loop) ────────────────────────
        while True:
            yield {"type": "node_start", "node": "codegen"}
            state = node_codegen(state)
            yield {
                "type": "node_done",
                "node": "codegen",
                "code": state.code,
                "retry": state.retry_count,
            }

            yield {"type": "node_start", "node": "executor"}
            state = node_executor(state, df)

            if state.error:
                yield {
                    "type": "node_error",
                    "node": "executor",
                    "error": state.error[:400],
                    "retry_count": state.retry_count,
                }
                if not state.should_retry:
                    # Max retries hit — give up
                    yield {"type": "error", "message": "Max retries reached. The agent could not produce working code."}
                    return
                # Loop back to codegen
                continue

            # Success
            yield {
                "type": "node_done",
                "node": "executor",
                "output": state.code_output,
                "chart_b64": state.chart_b64,
            }
            break

        # ── Interpreter ─────────────────────────────────────────────────
        yield {"type": "node_start", "node": "interpreter"}
        state = node_interpreter(state)
        yield {"type": "node_done", "node": "interpreter", "insights": state.insights}

        yield {"type": "done"}

    except requests.exceptions.HTTPError as e:
        yield {"type": "error", "message": f"Groq API error: {str(e)}"}
    except Exception as e:
        import traceback
        yield {"type": "error", "message": f"Agent error: {traceback.format_exc()[:500]}"}
