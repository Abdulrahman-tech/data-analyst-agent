// Sidebar.jsx
// Left panel showing:
//   1. LangGraph node list — lights up as the agent runs each node
//   2. Loaded dataset metadata
//   3. Sample queries to try

const NODES = [
  { id: 'parser',      label: 'Query Parser'  },
  { id: 'planner',     label: 'Planner'       },
  { id: 'codegen',     label: 'Code Generator'},
  { id: 'executor',    label: 'Executor'      },
  { id: 'interpreter', label: 'Interpreter'   },
]

const SAMPLES = [
  'What are the top 5 rows?',
  'Show a bar chart of revenue by category',
  'What is the average of each numeric column?',
  'Which month had the highest total revenue?',
  'Are there any missing values?',
]

export default function Sidebar({ nodeStates, dataset, onSample, onReset }) {
  return (
    <aside style={{
      background: 'var(--surface)',
      borderRight: '1px solid var(--border)',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
      overflowY: 'auto',
    }}>

      {/* ── Graph nodes ─────────────────────────────────────────────── */}
      <section>
        <Label>Agent Graph</Label>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {NODES.map((node, i) => {
            const s = nodeStates[node.id] || 'idle'
            return (
              <div key={node.id}>
                <NodeRow label={node.label} status={s} />
                {i < NODES.length - 1 && (
                  <div style={{ width: 1, height: 8, background: 'var(--border)', marginLeft: 19 }} />
                )}
              </div>
            )
          })}
        </div>
      </section>

      {/* ── Dataset info ────────────────────────────────────────────── */}
      {dataset && (
        <section>
          <Label>Dataset</Label>
          <div style={{
            background: 'rgba(45,212,191,0.06)',
            border: '1px solid rgba(45,212,191,0.2)',
            borderRadius: 8,
            padding: '10px 12px',
          }}>
            <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 3 }}>
              {dataset.filename}
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text3)' }}>
              {dataset.rows} rows · {dataset.columns} cols
            </div>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--text3)',
              marginTop: 6, lineHeight: 1.7,
            }}>
              {dataset.column_names.join(', ')}
            </div>
          </div>
          <button onClick={onReset} style={ghostBtn}>
            ↑ Upload different file
          </button>
        </section>
      )}

      {/* ── Sample queries ──────────────────────────────────────────── */}
      {dataset && (
        <section>
          <Label>Try These</Label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {SAMPLES.map(q => (
              <button key={q} onClick={() => onSample(q)} style={sampleBtn}>
                {q}
              </button>
            ))}
          </div>
        </section>
      )}
    </aside>
  )
}

// ── sub-components ────────────────────────────────────────────────────────────

function NodeRow({ label, status }) {
  const theme = {
    idle:   { border: 'var(--border)',            bg: 'var(--surface2)',           dot: 'var(--border2)', text: 'var(--text2)' },
    active: { border: 'var(--accent)',             bg: 'rgba(124,106,247,0.12)',   dot: 'var(--accent)',  text: 'var(--accent2)' },
    done:   { border: 'rgba(74,222,128,0.35)',     bg: 'rgba(74,222,128,0.06)',    dot: 'var(--green)',   text: 'var(--green)' },
    error:  { border: 'rgba(248,113,113,0.35)',    bg: 'rgba(248,113,113,0.06)',   dot: 'var(--red)',     text: 'var(--red)' },
  }[status]

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '7px 10px', borderRadius: 6,
      border: `1px solid ${theme.border}`,
      background: theme.bg,
      transition: 'all 0.25s',
    }}>
      <div style={{
        width: 7, height: 7, borderRadius: '50%',
        background: theme.dot, flexShrink: 0,
        boxShadow: status === 'active' ? `0 0 7px ${theme.dot}` : 'none',
        transition: 'all 0.25s',
      }} />
      <span style={{ fontSize: 11, fontWeight: 600, color: theme.text, flex: 1 }}>
        {label}
      </span>
      {status === 'active' && (
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--accent2)',
          animation: 'pulse 1.2s infinite',
        }}>
          running
        </span>
      )}
      {status === 'done'  && <span style={{ fontSize: 11, color: 'var(--green)' }}>✓</span>}
      {status === 'error' && <span style={{ fontSize: 11, color: 'var(--red)' }}>✗</span>}
    </div>
  )
}

function Label({ children }) {
  return (
    <div style={{
      fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '1.5px',
      color: 'var(--text3)', textTransform: 'uppercase', marginBottom: 8,
    }}>
      {children}
    </div>
  )
}

const ghostBtn = {
  marginTop: 8, width: '100%',
  background: 'transparent', border: '1px solid var(--border)',
  color: 'var(--text3)', fontFamily: 'var(--sans)', fontSize: 11,
  padding: '6px 10px', borderRadius: 6, cursor: 'pointer',
}

const sampleBtn = {
  background: 'var(--surface2)', border: '1px solid var(--border)',
  color: 'var(--text2)', fontFamily: 'var(--sans)', fontSize: 11,
  padding: '8px 10px', borderRadius: 6, cursor: 'pointer',
  textAlign: 'left', lineHeight: 1.45,
}
