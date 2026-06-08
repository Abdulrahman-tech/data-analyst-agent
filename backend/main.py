# main.py
# FastAPI server. Two main endpoints:
# POST /upload  → accepts CSV/JSON, returns dataset info
# POST /analyze → runs the LangGraph agent, streams progress back via SSE

import os
import json
import asyncio
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import agent
from tools import load_dataset
from state import AgentState

app = FastAPI(title="Data Analyst Agent")

# Allow the React dev server to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated charts as static files
os.makedirs("charts", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
app.mount("/charts", StaticFiles(directory="charts"), name="charts")


# ─── Models ───────────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    query: str
    dataset_path: str  # The path returned by /upload


# ─── Upload Endpoint ──────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts a CSV or JSON file.
    Saves it to disk, loads it with pandas, and returns dataset metadata.
    """
    if not file.filename.endswith((".csv", ".json")):
        raise HTTPException(400, "Only CSV and JSON files are supported.")

    # Save with unique name to avoid collisions
    file_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix
    save_path = f"uploads/{file_id}{ext}"

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Load and inspect with pandas
    try:
        df, dataset_info = load_dataset(save_path)
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(400, f"Could not parse file: {str(e)}")

    return {
        "dataset_path": save_path,
        "filename": file.filename,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "dataset_info": dataset_info,
    }


# ─── Analyze Endpoint (SSE Streaming) ────────────────────────────────────────
@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Runs the full LangGraph agent pipeline.
    Streams progress updates back to the frontend using Server-Sent Events (SSE).

    SSE format: each message is "data: {json}\\n\\n"
    The frontend listens for these and updates the UI in real time.
    """
    if not os.path.exists(request.dataset_path):
        raise HTTPException(404, "Dataset not found. Please re-upload your file.")

    # Load dataset info for the agent
    _, dataset_info = load_dataset(request.dataset_path)

    async def stream_agent() -> AsyncGenerator[str, None]:
        # Helper to send an SSE event
        def event(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        try:
            # Send initial state
            yield event({"type": "start", "message": "Agent starting..."})

            # Build initial state for the graph
            initial_state: AgentState = {
                "user_query": request.query,
                "dataset_path": request.dataset_path,
                "dataset_info": dataset_info,
                "intent": "",
                "plan": [],
                "code": "",
                "code_output": "",
                "chart_path": None,
                "error": None,
                "retry_count": 0,
                "insights": "",
                "steps_log": [],
            }

            # Stream through each node of the graph
            # LangGraph's .astream() yields state after each node completes
            async for chunk in agent.astream(initial_state):
                node_name = list(chunk.keys())[0]
                node_state = chunk[node_name]

                if node_name == "parser":
                    yield event({
                        "type": "node_complete",
                        "node": "parser",
                        "intent": node_state.get("intent", ""),
                    })

                elif node_name == "planner":
                    yield event({
                        "type": "node_complete",
                        "node": "planner",
                        "plan": node_state.get("plan", []),
                    })

                elif node_name == "codegen":
                    yield event({
                        "type": "node_complete",
                        "node": "codegen",
                        "code": node_state.get("code", ""),
                        "retry": node_state.get("retry_count", 0) > 0,
                    })

                elif node_name == "executor":
                    if node_state.get("error"):
                        yield event({
                            "type": "node_error",
                            "node": "executor",
                            "error": node_state["error"][:300],
                            "retry_count": node_state.get("retry_count", 0),
                        })
                    else:
                        yield event({
                            "type": "node_complete",
                            "node": "executor",
                            "output": node_state.get("code_output", ""),
                            "chart_path": node_state.get("chart_path"),
                        })

                elif node_name == "interpreter":
                    yield event({
                        "type": "node_complete",
                        "node": "interpreter",
                        "insights": node_state.get("insights", ""),
                    })

                # Small delay so the frontend can process each event
                await asyncio.sleep(0.05)

            yield event({"type": "done"})

        except Exception as e:
            yield event({"type": "error", "message": str(e)})

    return StreamingResponse(
        stream_agent(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
