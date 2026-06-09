# app.py
# Flask server with two endpoints:
#   POST /upload   → accepts CSV/JSON, returns dataset metadata
#   POST /analyze  → runs the agent, streams SSE events back

import io
import json
import logging
import os
import uuid

import pandas as pd
from flask import Flask, Response, request, jsonify, stream_with_context
from dotenv import load_dotenv

from agent import run_graph
from tools import get_dataset_info

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", 10))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_DATASETS = int(os.environ.get("MAX_DATASETS", 100))  # evict oldest after this

# In-memory dataset store: session_id → DataFrame
# For a production app you'd use Redis or a tmp file, but this works well here
DATASETS: dict[str, pd.DataFrame] = {}


# ── CORS ──────────────────────────────────────────────────────────────────────
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
if FRONTEND_URL and not FRONTEND_URL.startswith("http"):
    FRONTEND_URL = "https://" + FRONTEND_URL

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = FRONTEND_URL
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/upload", methods=["OPTIONS"])
@app.route("/analyze", methods=["OPTIONS"])
def options():
    return "", 204


# ── Helpers ───────────────────────────────────────────────────────────────────
def evict_oldest_datasets():
    """Keep memory usage bounded by removing oldest entries when limit is hit."""
    while len(DATASETS) >= MAX_DATASETS:
        oldest_key = next(iter(DATASETS))
        del DATASETS[oldest_key]
        logger.info(f"Evicted dataset {oldest_key} (limit={MAX_DATASETS})")


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

    raw = file.read()

    # ── File size guard ───────────────────────────────────────────────────────
    if len(raw) > MAX_FILE_SIZE_BYTES:
        return jsonify({
            "error": f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB."
        }), 413

    # ── Parse ─────────────────────────────────────────────────────────────────
    try:
        if filename.endswith(".json"):
            df = pd.read_json(io.BytesIO(raw))
        else:
            df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        logger.warning(f"Failed to parse file '{filename}': {e}")
        return jsonify({"error": f"Could not parse file: {e}"}), 400

    # ── Empty file guard ──────────────────────────────────────────────────────
    if df.empty:
        return jsonify({"error": "The uploaded file is empty."}), 400

    # ── Store ─────────────────────────────────────────────────────────────────
    evict_oldest_datasets()
    dataset_id = str(uuid.uuid4())[:8]
    DATASETS[dataset_id] = df

    logger.info(f"Uploaded '{filename}' → dataset_id={dataset_id} shape={df.shape}")

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
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    query = body.get("query", "").strip()
    dataset_id = body.get("dataset_id", "").strip()

    # ── Input validation ──────────────────────────────────────────────────────
    if not query:
        return jsonify({"error": "query is required"}), 400

    if len(query) > 1000:
        return jsonify({"error": "Query too long. Please keep it under 1000 characters."}), 400

    if not dataset_id or dataset_id not in DATASETS:
        return jsonify({
            "error": "Dataset not found. The server may have restarted — please re-upload your file."
        }), 404

    df = DATASETS[dataset_id]
    dataset_info = get_dataset_info(df)
    dataset_json = df.to_json()

    logger.info(f"Analyze request: dataset_id={dataset_id} query='{query[:80]}'")

    def generate():
        try:
            for event in run_graph(query, dataset_json, dataset_info, df):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'An unexpected server error occurred.'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Tells nginx/Railway not to buffer SSE
        },
    )


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    groq_key_set = bool(os.environ.get("GROQ_API_KEY"))
    return jsonify({
        "status": "ok",
        "datasets_loaded": len(DATASETS),
        "groq_key_configured": groq_key_set,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
    })


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        logger.warning("GROQ_API_KEY is not set — agent calls will fail!")
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Data Analyst Agent backend on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
