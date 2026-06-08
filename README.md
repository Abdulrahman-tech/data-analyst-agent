# 🤖 Data Analyst Agent

An AI agent that takes natural language questions about your data, plans the analysis, writes and executes Python code, generates charts, and explains the results — all in real time.

Built with a **LangGraph-style multi-node pipeline** powered by **Groq (llama-3.3-70b)**.

![Demo](https://i.imgur.com/placeholder.png)

---

## ✨ Features

- 🔍 **Query Parser** — understands what you're asking in plain English
- 📋 **Planner** — breaks the analysis into ordered steps
- 💻 **Code Generator** — writes real pandas + matplotlib Python code
- ⚙️ **Executor** — runs the code, captures output and charts
- 💡 **Interpreter** — explains findings in plain English
- 🔁 **Auto-retry** — if code fails, the agent fixes it and tries again
- 📡 **Live streaming** — watch each node run in real time via SSE

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| LLM | Groq — llama-3.3-70b-versatile |
| Agent pipeline | LangGraph-style state machine |
| Backend | Flask + Server-Sent Events |
| Data analysis | pandas, matplotlib |
| Frontend | React + Vite |

---

## 🚀 Running Locally

### 1. Get a free Groq API key
Go to [console.groq.com](https://console.groq.com) → API Keys → Create key

### 2. Backend
```bash
cd backend
pip install flask python-dotenv pandas matplotlib seaborn numpy requests
cp .env.example .env
# paste your Groq key into .env
python app.py
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## 🧠 How It Works
---

## 📊 Sample Queries to Try

- *"Show a bar chart of total revenue by category"*
- *"Which month had the highest revenue?"*
- *"Plot revenue trend over time for Electronics"*
- *"What is the average units sold per region?"*
- *"Are there any missing values?"*
