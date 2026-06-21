# agent.py
import os
import json
import logging
import requests
from dotenv import load_dotenv
from langsmith import traceable

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
            f"Dataset info:\n{state.dataset_info}\n\n"
            f'User question: "{state.user_query}"'
        ),
    )
    state.intent = reply
    state.steps_log.append({"node": "parser", "status": "done", "intent": reply})
    logger.info(f"Parser → intent: {reply[:100]}")
    return state


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
    logger.info(f"Planner → {len(plan)} steps")
    return state


@traceable(name="3. Code Generator")
def node_codegen(state: AgentState) -> AgentState:
    error_context = ""
    if state.error:
        error_context = (
            f"\n\nYour previous code raised this error:\n{state.error}\n"
            "Fix it. Try a completely different approach if needed."
        )
    plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(state.plan))
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
            f"Dataset info:\n{state.dataset_info}\n\n"
            f"Plan:\n{plan_text}\n\n"
            f"wants_chart: {user_wants_chart(state.user_query)}\n"
            f"{error_context}"
        ),
    )
    state.code = extract_code(raw)
    state.error = None
    state.steps_log.append({
        "node": "codegen",
        "status": "done",
        "code": state.code,
        "retry": state.retry_count,
    })
    logger.info(f"CodeGen → {len(state.code)} chars (retry={state.retry_count})")
    return state


@traceable(name="4. Executor")
def node_executor(state: AgentState, df) -> AgentState:
    output, chart_html, error = run_code(state.code, df)
    if error:
        state.error = error
        state.retry_count += 1
        state.should_retry = state.retry_count < MAX_RETRIES
        logger.warning(f"Executor error (retry {state.retry_count}/{MAX_RETRIES}): {error[:200]}")
        state.steps_log.append({
            "node": "executor",
            "status": "error",
            "error": error[:400],
            "retry_count": state.retry_count,
        })
    else:
        truncated_output = output[:MAX_OUTPUT_CHARS]
        if len(output) > MAX_OUTPUT_CHARS:
            truncated_output += f"\n... (output truncated at {MAX_OUTPUT_CHARS} chars)"
        state.code_output = truncated_output
        state.chart_html = chart_html
        state.error = None
        state.should_retry = False
        logger.info(f"Executor success → output={len(output)} chars, chart={'yes' if chart_html else 'no'}")
        state.steps_log.append({
            "node": "executor",
            "status": "done",
            "output": truncated_output,
            "has_chart": chart_html is not None,
        })
    return state


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
            f'Original question: "{state.user_query}"\n\n'
            f"Code output:\n{state.code_output}"
        ),
        temperature=0.3,
    )
    state.insights = reply
    state.steps_log.append({"node": "interpreter", "status": "done", "insights": reply})
    logger.info("Interpreter → insights generated")
    return state


def run_graph(user_query: str, dataset_json: str, dataset_info: str, df):
    state = AgentState(
        user_query=user_query,
        dataset_json=dataset_json,
        dataset_info=dataset_info,
    )
    try:
        yield {"type": "node_start", "node": "parser"}
        state = node_parser(state)
        yield {"type": "node_done", "node": "parser", "intent": state.intent}

        yield {"type": "node_start", "node": "planner"}
        state = node_planner(state)
        yield {"type": "node_done", "node": "planner", "plan": state.plan}

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
                    yield {
                        "type": "error",
                        "message": f"The agent could not produce working code after {MAX_RETRIES} attempts."
                    }
                    return
                continue

            yield {
                "type": "node_done",
                "node": "executor",
                "output": state.code_output,
                "chart_html": state.chart_html,
            }
            break

        yield {"type": "node_start", "node": "interpreter"}
        state = node_interpreter(state)
        yield {"type": "node_done", "node": "interpreter", "insights": state.insights}

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
