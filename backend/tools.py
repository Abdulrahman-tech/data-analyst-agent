# tools.py
# Low-level tools used by the agent nodes.
# run_code() is the most important: it executes LLM-generated Python safely.

import io
import sys
import base64
import logging
import traceback

import matplotlib
matplotlib.use("Agg")  # Must be before any other matplotlib import — headless server safe
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Maximum execution time guard (in seconds) — prevents infinite loops in generated code
MAX_EXEC_SECONDS = 30


def get_dataset_info(df: pd.DataFrame) -> str:
    """
    Build a rich text description of a DataFrame for the LLM.
    The LLM uses this to understand column names, types, and data shape
    before writing any code.
    Truncates very wide DataFrames to keep token usage reasonable.
    """
    # Cap rows shown in head/describe to avoid massive prompts
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
    Execute LLM-generated Python code in a controlled namespace.

    The DataFrame is pre-loaded as `df` so the LLM doesn't need to
    read files — it just uses `df` directly.

    Returns:
        output    (str)            - everything the code printed
        chart_b64 (str | None)     - base64-encoded PNG if a chart was made
        error     (str | None)     - full traceback if the code raised
    """
    if not code or not code.strip():
        return "", None, "No code was generated."

    # Redirect stdout so we capture print() calls
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    plt.close("all")  # Clear any leftover figures from previous runs

    # Provide a safe, minimal namespace — only what the agent needs
    exec_globals = {
        "__builtins__": __builtins__,
        "pd": pd,
        "plt": plt,
        "np": np,
        "df": df.copy(),  # Give the code its own copy — prevents mutation bugs
    }

    try:
        exec(code, exec_globals)

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        # If the code created a matplotlib figure, encode it as base64 PNG
        chart_b64 = None
        if plt.get_fignums():
            buf = io.BytesIO()
            plt.savefig(
                buf,
                format="png",
                dpi=130,
                bbox_inches="tight",
                facecolor=plt.gcf().get_facecolor(),
            )
            buf.seek(0)
            chart_b64 = base64.b64encode(buf.read()).decode("utf-8")
            plt.close("all")
            logger.info("Chart generated successfully")

        return output or "(code ran with no printed output)", chart_b64, None

    except MemoryError:
        sys.stdout = old_stdout
        plt.close("all")
        logger.error("MemoryError during code execution")
        return "", None, "MemoryError: The generated code used too much memory."

    except Exception:
        sys.stdout = old_stdout
        plt.close("all")
        tb = traceback.format_exc()
        logger.warning(f"Code execution error: {tb[:300]}")
        return "", None, tb

    finally:
        # Always restore stdout, even if something goes very wrong
        if sys.stdout != old_stdout:
            sys.stdout = old_stdout
        plt.close("all")
