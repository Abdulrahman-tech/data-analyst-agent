# Data Analyst Agent

A full-stack AI agent that takes natural language questions about your CSV/JSON data,
plans the analysis, writes and executes Python code, generates charts, and explains results.

**Stack:** Flask · Groq (llama-3.3-70b) · pandas · matplotlib · React · Vite

---

## Project Structure

```
data-analyst-agent/
├── backend/
│   ├── app.py           ← Flask server (upload + SSE streaming)
│   ├── agent.py         ← 5-node agent pipeline (LangGraph-style)
│   ├── state.py         ← Shared state dataclass
│   ├── tools.py         ← Code executor + dataset loader
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx               ← Root: owns state + SSE reader
│   │   ├── components/
│   │   │   ├── Sidebar.jsx       ← Node graph + dataset info
│   │   │   ├── FileUpload.jsx    ← Drag-and-drop uploader
│   │   │   └── Messages.jsx      ← Chat: renders all block types
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── sample_data.csv      ← Test dataset (12 months, 3 categories)
```

---

## Setup (do this once)

### 1. Get a free Groq API key
Go to https://console.groq.com → sign up → API Keys → Create key

### 2. Backend
```bash
cd backend

# Install dependencies
pip install flask python-dotenv pandas matplotlib seaborn numpy requests

# Add your API key
cp .env.example .env
# Open .env and replace  your_groq_key_here  with your real key

# Start the server
python app.py
```
You should see: `Starting Data Analyst Agent backend on http://localhost:5000`

### 3. Frontend (new terminal tab)
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**

---

## How the agent works

```
User query
    │
    ▼
[Parser]      → "User wants a bar chart of revenue grouped by category"
    │
    ▼
[Planner]     → ["Group by category", "Sum revenue", "Plot bar chart"]
    │
    ▼
[CodeGen]     → writes pandas + matplotlib Python code
    │
    ▼
[Executor]    → runs the code, captures output + chart
    │  ↑
    │  └── on error: sends traceback back to CodeGen (up to 3 retries)
    ▼
[Interpreter] → "Electronics leads with $102k, 4× higher than Food..."
```

Each node calls Groq's llama-3.3-70b model.
Results stream back to the UI live via Server-Sent Events (SSE).

---

## Try these queries on sample_data.csv

- `What are the top 5 rows?`
- `Show a bar chart of total revenue by category`
- `Which month had the highest revenue?`
- `Plot revenue trend over time for Electronics`
- `What is the average units_sold per region?`
- `Show a pie chart of revenue share by category`
- `Are there any missing values?`
