# tools.py
# Low-level tools used by the agent nodes.
# run_code() is the most important: it executes LLM-generated Python safely.

import io
import sys
import base64
import traceback

import matplotlib
matplotlib.use("Agg")  # Must be before any other matplotlib import
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def get_dataset_info(df: pd.DataFrame) -> str:
    """
    Build a rich text description of a DataFrame for the LLM.
    The LLM uses this to understand column names, types, and data shape
    before writing any code.
    """
    return f"""Columns: {list(df.columns)}
Shape: {df.shape[0]} rows x {df.shape[1]} columns

Column types:
{df.dtypes.to_string()}

First 5 rows:
{df.head().to_string()}

Descriptive statistics:
{df.describe(include='all').to_string()}

Missing values per column:
{df.isnull().sum().to_string()}"""


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
    # Redirect stdout so we capture print() calls
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    plt.close("all")  # Clear any leftover figures

    exec_globals = {
        "pd": pd,
        "plt": plt,
        "np": np,
        "df": df.copy(),  # Give the code its own copy — prevents mutation bugs
    }

    try:
        exec(code, exec_globals)

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        # If the code created a matplotlib figure, encode it as base64
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

        return output or "(code ran with no printed output)", chart_b64, None

    except Exception:
        sys.stdout = old_stdout
        plt.close("all")
        return "", None, traceback.format_exc()
