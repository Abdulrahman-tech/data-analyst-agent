# app.py
# Flask server with two endpoints:
#   POST /upload   → accepts CSV/JSON, returns dataset metadata
#   POST /analyze  → runs the agent, streams SSE events back

import io
import json
import os
import uuid

import pandas as pd
from flask import Flask, Response, request, jsonify, stream_with_context
from dotenv import load_dotenv

from agent import run_graph
from tools import get_dataset_info

load_dotenv()

app = Flask(__name__)

# In-memory dataset store: session_id → DataFrame
# For a production app you'd use Redis or a tmp file, but this is fine for local use
DATASETS: dict[str, pd.DataFrame] = {}


# ── CORS (allow React dev server on port 5173) ────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/upload", methods=["OPTIONS"])
@app.route("/analyze", methods=["OPTIONS"])
def options():
    return "", 204


# ── Upload endpoint ───────────────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload():
    """
    Accepts a CSV or JSON file.
    Stores the DataFrame in memory and returns metadata the frontend needs.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file sent"}), 400

    file = request.files["file"]
    filename = file.filename or ""

    if not filename.endswith((".csv", ".json")):
        return jsonify({"error": "Only CSV and JSON files are supported"}), 400

    try:
        raw = file.read()
        if filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(raw))
        else:
            df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400

    # Give this dataset a unique ID so we can look it up during /analyze
    dataset_id = str(uuid.uuid4())[:8]
    DATASETS[dataset_id] = df

    return jsonify({
        "dataset_id": dataset_id,
        "filename": filename,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "dataset_info": get_dataset_info(df),
    })


# ── Analyze endpoint (SSE) ────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Runs the full agent pipeline and streams progress as Server-Sent Events.
    Each event is:   data: {...json...}\\n\\n
    The frontend reads these and updates the UI node-by-node in real time.
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    query = body.get("query", "").strip()
    dataset_id = body.get("dataset_id", "").strip()

    if not query:
        return jsonify({"error": "query is required"}), 400
    if not dataset_id or dataset_id not in DATASETS:
        return jsonify({"error": "Dataset not found. Please re-upload your file."}), 404

    df = DATASETS[dataset_id]
    dataset_info = get_dataset_info(df)
    dataset_json = df.to_json()

    def generate():
        for event in run_graph(query, dataset_json, dataset_info, df):
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # Tells nginx not to buffer SSE
        },
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "datasets_loaded": len(DATASETS)})


if __name__ == "__main__":
    print("Starting Data Analyst Agent backend on http://localhost:5000")
    print("Make sure GROQ_API_KEY is set in backend/.env")
    app.run(debug=True, port=5001, threaded=True)
