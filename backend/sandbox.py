import sys
import io
import json
import traceback
import pandas as pd
import numpy as np


def main():
    try:
        payload = json.loads(sys.stdin.read())
        code = payload["code"]
        data = json.loads(payload["data"])
        df = pd.DataFrame(data)
    except Exception as e:
        print(json.dumps({"output": "", "chart_html": None, "error": f"Input error: {e}"}))
        return

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    exec_globals = {
        "__builtins__": __builtins__,
        "pd": pd,
        "np": np,
        "df": df,
    }

    try:
        import plotly.graph_objects as go
        import plotly.express as px
        exec_globals["go"] = go
        exec_globals["px"] = px
    except ImportError:
        pass

    chart_html = None

    try:
        exec(code, exec_globals)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        try:
            import plotly.graph_objects as go
            from plotly.io import to_html
            for val in exec_globals.values():
                if isinstance(val, go.Figure):
                    raw_html = to_html(
                        val,
                        full_html=False,
                        include_plotlyjs="cdn",
                        config={
                            "scrollZoom": True,
                            "displayModeBar": True,
                            "toImageButtonOptions": {"format": "png", "scale": 2}
                        }
                    )
                    chart_html = raw_html.replace("\n", " ")
                    break
        except Exception:
            pass

        print(json.dumps({
            "output": output or "(code ran with no printed output)",
            "chart_html": chart_html,
            "error": None
        }))

    except Exception:
        sys.stdout = old_stdout
        tb = traceback.format_exc()
        print(json.dumps({
            "output": "",
            "chart_html": None,
            "error": tb
        }))


if __name__ == "__main__":
    main()
