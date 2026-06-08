// AgentSteps.jsx
// The left sidebar showing the LangGraph nodes and their live status.
// Each node lights up as the agent processes it.

const NODES = [
  { id: 'parser',      label: 'Query Parser',   icon: '🔍' },
  { id: 'planner',     label: 'Planner',         icon: '📋' },
  { id: 'codegen',     label: 'Code Generator',  icon: '💻' },
  { id: 'executor',    label: 'Executor',         icon: '⚙️' },
  { id: 'interpreter', label: 'Interpreter',      icon: '💡' },
]

export default function AgentSteps({ nodeStates, dataset }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', padding: '0 4px' }}>
      {NODES.map((node, i) => {
        const state = nodeStates[node.id] // 'idle' | 'active' | 'done' | 'error'

        const colors = {
          idle:   { border: 'var(--border)',  bg: 'var(--surface2)', dot: 'var(--border2)', text: 'var(--text2)' },
          active: { border: 'var(--accent)',  bg: 'rgba(124,106,247,0.12)', dot: 'var(--accent)', text: 'var(--accent2)' },
          done:   { border: 'rgba(74,222,128,0.3)', bg: 'rgba(74,222,128,0.06)', dot: 'var(--green)', text: 'var(--green)' },
          error:  { border: 'rgba(248,113,113,0.3)', bg: 'rgba(248,113,113,0.06)', dot: 'var(--red)', text: 'var(--red)' },
        }[state || 'idle']

        return (
          <div key={node.id}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '8px 10px',
              borderRadius: '6px',
              border: `1px solid ${colors.border}`,
              background: colors.bg,
              transition: 'all 0.3s',
            }}>
              {/* Status dot */}
              <div style={{
                width: '7px', height: '7px', borderRadius: '50%',
                background: colors.dot,
                flexShrink: 0,
                boxShadow: state === 'active' ? `0 0 8px ${colors.dot}` : 'none',
                transition: 'all 0.3s',
              }}/>
              <span style={{ fontSize: '11px', fontWeight: 600, color: colors.text }}>
                {node.label}
              </span>
              {state === 'active' && (
                <span style={{
                  marginLeft: 'auto',
                  fontFamily: 'var(--mono)',
                  fontSize: '9px',
                  color: 'var(--accent2)',
                  animation: 'pulse 1s infinite',
                }}>
                  running
                </span>
              )}
              {state === 'done' && (
                <span style={{ marginLeft: 'auto', fontSize: '11px' }}>✓</span>
              )}
              {state === 'error' && (
                <span style={{ marginLeft: 'auto', fontSize: '11px' }}>✗</span>
              )}
            </div>

            {/* Connector line between nodes */}
            {i < NODES.length - 1 && (
              <div style={{
                width: '1px',
                height: '8px',
                background: 'var(--border)',
                margin: '0 auto 0 20px',
              }}/>
            )}
          </div>
        )
      })}

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
      `}</style>

      {/* Dataset info */}
      {dataset && (
        <div style={{
          marginTop: '16px',
          background: 'rgba(45,212,191,0.06)',
          border: '1px solid rgba(45,212,191,0.2)',
          borderRadius: '8px',
          padding: '10px 12px',
        }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--teal)', letterSpacing: '1px', marginBottom: '6px' }}>
            DATASET
          </div>
          <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '2px' }}>
            {dataset.filename}
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)' }}>
            {dataset.rows} rows · {dataset.columns} cols
          </div>
          <div style={{
            fontFamily: 'var(--mono)',
            fontSize: '9px',
            color: 'var(--text3)',
            marginTop: '6px',
            lineHeight: 1.6,
          }}>
            {dataset.column_names.join(', ')}
          </div>
        </div>
      )}
    </div>
  )
}
