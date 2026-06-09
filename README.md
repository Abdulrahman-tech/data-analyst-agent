[# dataanalyst.agent

An AI-powered data analysis agent that lets you query any CSV or JSON dataset using plain English. Upload your data, ask a question, and watch the agent plan, write code, execute it, and explain the results — live.

**[🚀 Live Demo](https://data-analyst-agent-azeb0ylxe-atech-s-projects.vercel.app)**

![dataanalyst.agent screenshot](Screenshot%202026-06-08%20at%2017.32.38.png)

---

## How it works

The agent runs a 5-node LangGraph-style pipeline, streaming each step to the UI in real time:

```
Query Parser → Planner → Code Generator → Executor → Interpreter
                                ↑               │
                                └───────────────┘
                                  (auto-retry on error)
```

| Node | What it does |
|------|-------------|
| **Query Parser** | Understands your intent and identifies relevant columns |
| **Planner** | Breaks the analysis into 3–5 ordered steps |
| **Code Generator** | Writes executable pandas/matplotlib Python code |
| **Executor** | Runs the code, captures output and charts. Auto-retries up to 3× on failure |
| **Interpreter** | Translates results into plain-English insights with actionable recommendations |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Agent pipeline | Hand-rolled LangGraph-style state machine |
| Backend | Python · Flask · Server-Sent Events (SSE) |
| Data | pandas · matplotlib · seaborn · numpy |
| Frontend | React · Vite |
| Backend hosting | Railway |
| Frontend hosting | Vercel |

---

## Features

- 📁 Upload any CSV or JSON file (up to 10MB)
- 💬 Ask questions in plain English — no SQL or code required
- 📊 Auto-generates charts with dark theme styling
- 🔁 Agent auto-retries with error context if generated code fails
- ⚡ Real-time streaming — watch each node activate live
- 🔒 Input validation, file size guards, and graceful error handling

---

## Example queries

- *"Show a bar chart of revenue by category"*
- *"Which month had the highest total revenue?"*
- *"What is the average units sold per region?"*
- *"Are there any missing values?"*
- *"Show the top 5 rows"*

---

## Run locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env file
echo "GROQ_API_KEY=your_key_here" > .env

python app.py
# Runs on http://localhost:5000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

---

## Project structure

```
data-analyst-agent/
├── backend/
│   ├── app.py          # Flask server — /upload and /analyze endpoints
│   ├── agent.py        # 5-node agent pipeline with SSE streaming
│   ├── tools.py        # Code execution sandbox + dataset info builder
│   ├── state.py        # AgentState dataclass shared across all nodes
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Root component — SSE reader + state
│   │   └── components/
│   │       ├── Sidebar.jsx   # Agent graph + dataset info panel
│   │       ├── FileUpload.jsx
│   │       └── Messages.jsx  # Chat-style results renderer
│   └── vite.config.js
└── sample_data.csv
```

---

## Architecture decisions

**Why SSE instead of WebSockets?**
SSE is simpler for unidirectional server-to-client streaming. Since the agent only pushes events to the frontend (never the reverse during a run), SSE is the right tool — no handshake overhead, native browser support, and automatic reconnection.

**Why Groq instead of OpenAI?**
Groq's inference speed is significantly faster for `llama-3.3-70b`, which matters when you're making 4–5 sequential LLM calls per query. The free tier is also generous enough for a portfolio project.

**Why a hand-rolled pipeline instead of LangGraph?**
Building the state machine manually gives full control over the SSE streaming — LangGraph's abstractions make it harder to yield events mid-graph. It also keeps the codebase dependency-light and easy to understand.

---

## What I'd add with more time

- [ ] Redis-backed dataset storage (replace in-memory dict)
- [ ] Multi-turn conversation memory within a session
- [ ] Support for Excel (.xlsx) files
- [ ] Export results as PDF report
- [ ] User authentication for saved sessions

---

## Contact

Built by **Abdulrahman** — open to freelance projects and full-time roles in AI engineering and full-stack development.

- GitHub: [Abdulrahman-tech](https://github.com/Abdulrahman-tech)
- LinkedIn: *[your LinkedIn URL]*

> If you'd like a custom version of this agent for your business — DM me.]
