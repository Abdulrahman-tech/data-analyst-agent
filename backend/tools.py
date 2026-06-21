# tools.py
import io
import sys
import base64
import logging
import traceback
import subprocess
import json

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def get_dataset_info(df: pd.DataFrame) -> str:
    sample_rows = min(5, len(df))
    return (
        f"Columns: {list(df.columns)}\n"
        f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n\n"
        f"Column types:\n{df.dtypes.to_string()}\n\n"
        f"First {sample_rows} rows:\n{df.head(sample_rows).to_string()}\n\n"
        f"Descriptive statistics:\n{df.describe(include='all').to_string()}\n\n"
        f"Missing values per column:\n{df.isnull().sum().to_string()}"
    )


def run_code(code: str, df: pd.DataFrame):
    """
    Execute LLM-generated Python code in an isolated subprocess.
    Returns: output (str), chart_html (str | None), error (str | None)
    """
    if not code or not code.strip():
        return "", None, "No code was generated."

    payload = json.dumps({
        "code": code,
        "data": df.to_json(orient="records")
    })

    try:
        result = subprocess.run(
            ["python", "sandbox.py"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=__file__.rsplit("/", 1)[0]
        )

        if result.returncode != 0:
            error = result.stderr.strip() or "Sandbox process failed."
            logger.warning(f"Sandbox error: {error[:300]}")
            return "", None, error

        response = json.loads(result.stdout)
        return (
            response.get("output", ""),
            response.get("chart_html", None),
            response.get("error", None)
        )

    except subprocess.TimeoutExpired:
        return "", None, "Code execution timed out after 30 seconds."

    except json.JSONDecodeError as e:
        return "", None, f"Sandbox returned invalid response: {e}"

    except Exception as e:
        logger.error(f"Sandbox runner error: {traceback.format_exc()}")
        return "", None, str(e)
