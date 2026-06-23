// App.jsx
// Root component. Owns all state and the SSE reading loop.
//
// State:
//   dataset     → what /upload returned (null until file is uploaded)
//   messages    → chat history [{role, text} | {role, blocks[]}]
//   nodeStates  → {parser|planner|codegen|executor|interpreter: 'idle'|'active'|'done'|'error'}
//   query       → current textarea value
//   running     → true while the agent is streaming

import { useState, useRef, useEffect } from 'react'
import Sidebar from './components/Sidebar.jsx'
import FileUpload from './components/FileUpload.jsx'
import Messages from './components/Messages.jsx'

const INITIAL_NODES = {
  parser: 'idle', planner: 'idle', codegen: 'idle',
  executor: 'idle', interpreter: 'idle',
  suggester: 'idle', detector: 'idle',
}

// Which node activates after each node completes
const NEXT_NODE = {
  parser: 'planner', planner: 'codegen',
  codegen: 'executor', executor: 'interpreter',
}

export default function App() {
  const [dataset,    setDataset]    = useState(null)
  const [messages,   setMessages]   = useState([])
  const [nodeStates, setNodeStates] = useState(INITIAL_NODES)
  const [query,      setQuery]      = useState('')
  const [running,    setRunning]    = useState(false)
  const [history,    setHistory]    = useState([])  // conversation memory
  const textareaRef = useRef()
  const currentQuery = useRef('')  // track query for history

  // ── Handle suggestion clicks ────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      setQuery(e.detail)
      textareaRef.current?.focus()
    }
    window.addEventListener('suggestion', handler)
    return () => window.removeEventListener('suggestion', handler)
  }, [])

  // ── Append a block to the last agent message ────────────────────────────
  function pushBlock(block) {
    setMessages(prev => {
      const updated = [...prev]
      const last = { ...updated[updated.length - 1] }
      last.blocks = [...(last.blocks || []), block]
      updated[updated.length - 1] = last
      return updated
    })
  }

  // ── Handle one SSE event dict ───────────────────────────────────────────
  function handleEvent(event) {
    const { type, node } = event

    if (type === 'node_start') {
      setNodeStates(prev => ({ ...prev, [node]: 'active' }))
    }

    if (type === 'node_done') {
      setNodeStates(prev => ({ ...prev, [node]: 'done' }))

      if (node === 'parser')      pushBlock({ type: 'intent', text: event.intent })
      if (node === 'planner')     pushBlock({ type: 'plan',   steps: event.plan })
      if (node === 'codegen')     pushBlock({ type: 'code',   code: event.code, retry: event.retry })
      if (node === 'executor') {
        if (event.output)    pushBlock({ type: 'output', text: event.output })
        if (event.chart_html) pushBlock({ type: 'chart', html: event.chart_html })
      }
      if (node === 'interpreter') {
        pushBlock({ type: 'insights', text: event.insights })
        setHistory(prev => [...prev, { query: currentQuery.current, insights: event.insights }])
      }
      if (node === 'suggester' && event.suggestions?.length) pushBlock({ type: 'suggestions', items: event.suggestions })
      if (node === 'detector' && event.patterns?.length) pushBlock({ type: 'patterns', items: event.patterns })
    }

    if (type === 'node_error') {
      setNodeStates(prev => ({ ...prev, executor: 'error', codegen: 'active' }))
      pushBlock({ type: 'error', error: event.error, retry_count: event.retry_count })
    }

    if (type === 'error') {
      pushBlock({ type: 'error', error: event.message })
    }
  }

  // ── Main: send query, read SSE stream ───────────────────────────────────
  async function runAgent() {
    const q = query.trim()
    if (!q || running || !dataset) return

    currentQuery.current = q
    setQuery('')
    textareaRef.current.style.height = 'auto'
    setRunning(true)
    setNodeStates(INITIAL_NODES)

    // Add user bubble
    setMessages(prev => [...prev, { role: 'user', text: q }])
    // Add empty agent bubble we'll fill as events arrive
    setMessages(prev => [...prev, { role: 'agent', blocks: [] }])

    try {
      const res = await fetch((import.meta.env.VITE_API_URL || '') + '/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, dataset_id: dataset.dataset_id, history }),
      })

      if (!res.ok) {
        const err = await res.json()
        pushBlock({ type: 'error', error: err.error || 'Server error' })
        setRunning(false)
        return
      }

      // Read the SSE stream line-by-line
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()   // keep incomplete line in buffer

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try { handleEvent(JSON.parse(raw)) } catch { /* skip malformed */ }
        }
      }
    } catch (e) {
      pushBlock({ type: 'error', error: e.message })
    }

    setRunning(false)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runAgent() }
  }

  function handleReset() {
    setDataset(null)
    setMessages([])
    setNodeStates(INITIAL_NODES)
    setHistory([])
  }

  // ── Render ──────────────────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: isMobile ? '1fr' : '255px 1fr',
      gridTemplateRows: '52px 1fr',
      height: '100vh',
    }}>

      {/* Header */}
      <header style={{
        gridColumn: '1 / -1',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', padding: '0 20px', gap: 12,
      }}>
        {isMobile && (
          <button
            onClick={() => setSidebarOpen(o => !o)}
            style={{
              background: 'none', border: 'none', color: 'var(--text)',
              fontSize: 20, cursor: 'pointer', padding: '4px 8px',
            }}
          >
            ☰
          </button>
        )}
        <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: '-0.5px' }}>
          data<span style={{ color: 'var(--accent2)' }}>analyst</span>.agent
        </span>
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 10,
          background: 'var(--surface3)', border: '1px solid var(--border2)',
          color: 'var(--text2)', padding: '2px 8px', borderRadius: 4, letterSpacing: '0.5px',
        }}>
          LANGGRAPH-STYLE
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          {running && (
            <span style={{
              fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--accent2)',
              animation: 'pulse 1.2s infinite',
            }}>
              agent running…
            </span>
          )}
          <span style={{
            fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--teal)',
            background: 'rgba(45,212,191,0.08)',
            border: '1px solid rgba(45,212,191,0.2)',
            padding: '2px 10px', borderRadius: 4,
          }}>
            groq · llama-3.3-70b
          </span>
        </div>
      </header>

      {/* Sidebar — hidden on mobile unless toggled */}
      {(!isMobile || sidebarOpen) && (
        <div style={{
          position: isMobile ? 'fixed' : 'relative',
          top: isMobile ? 52 : 'auto',
          left: 0,
          zIndex: isMobile ? 100 : 'auto',
          width: isMobile ? '255px' : 'auto',
          height: isMobile ? 'calc(100vh - 52px)' : 'auto',
          boxShadow: isMobile ? '4px 0 20px rgba(0,0,0,0.5)' : 'none',
        }}>
          <Sidebar
            nodeStates={nodeStates}
            dataset={dataset}
            onSample={q => { setQuery(q); textareaRef.current?.focus(); setSidebarOpen(false) }}
            onReset={handleReset}
          />
        </div>
      )}

      {/* Main */}
      <main style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Upload screen or chat */}
        {!dataset
          ? <FileUpload onUploaded={setDataset} />
          : <Messages messages={messages} />
        }

        {/* Input bar — only shown after upload */}
        {dataset && (
          <div style={{
            padding: '12px 20px',
            background: 'var(--surface)',
            borderTop: '1px solid var(--border)',
          }}>
            <div style={{
              display: 'flex', alignItems: 'flex-end', gap: 10,
              background: 'var(--surface2)',
              border: `1px solid ${running ? 'var(--accent)' : 'var(--border2)'}`,
              borderRadius: 10, padding: '9px 14px',
              transition: 'border-color 0.2s',
            }}>
              <textarea
                ref={textareaRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={running}
                placeholder="Ask anything about your data…"
                rows={1}
                style={{
                  flex: 1, background: 'transparent', border: 'none', outline: 'none',
                  color: 'var(--text)', fontFamily: 'var(--sans)', fontSize: 13,
                  resize: 'none', minHeight: 20, maxHeight: 120, lineHeight: 1.5,
                }}
                onInput={e => {
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
                }}
              />
              <button
                onClick={runAgent}
                disabled={running || !query.trim()}
                style={{
                  background: running || !query.trim() ? 'var(--surface3)' : 'var(--accent)',
                  border: 'none', color: '#fff',
                  width: 34, height: 34, borderRadius: 7,
                  cursor: running || !query.trim() ? 'not-allowed' : 'pointer',
                  fontSize: 15, flexShrink: 0, transition: 'background 0.2s',
                }}
              >
                {running ? '⏳' : '▶'}
              </button>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--text3)', marginTop: 6, textAlign: 'center' }}>
              Enter to send · Shift+Enter for new line
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
