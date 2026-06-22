// Messages.jsx
// Renders the full conversation.
// Agent messages are made of "blocks" — each block is a different content type:
//   intent, plan, code, error, output, chart, insights

import { useEffect, useRef } from 'react'

export default function Messages({ messages }) {
  const bottomRef = useRef()
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  return (
    <div style={{
      flex: 1, overflowY: 'auto', padding: '20px',
      display: 'flex', flexDirection: 'column', gap: 20,
    }}>
      {messages.map((msg, i) =>
        msg.role === 'user'
          ? <UserMessage key={i} text={msg.text} />
          : <AgentMessage key={i} blocks={msg.blocks} />
      )}
      <div ref={bottomRef} />
    </div>
  )
}

function UserMessage({ text }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, animation: 'fadeUp 0.3s ease' }}>
      <div style={{
        maxWidth: '70%', padding: '12px 16px', fontSize: 13, lineHeight: 1.65,
        background: 'rgba(124,106,247,0.12)',
        border: '1px solid rgba(124,106,247,0.25)',
        borderRadius: '10px 10px 3px 10px',
      }}>
        {text}
      </div>
      <Avatar color="#7c6af7">U</Avatar>
    </div>
  )
}

function AgentMessage({ blocks }) {
  return (
    <div style={{ display: 'flex', gap: 10, animation: 'fadeUp 0.3s ease' }}>
      <Avatar color="#2dd4bf">⬡</Avatar>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
        {blocks.map((block, i) => <Block key={i} block={block} />)}
      </div>
    </div>
  )
}

function Block({ block }) {
  switch (block.type) {

    case 'intent':
      return (
        <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text3)', paddingLeft: 2 }}>
          <span style={{ color: 'var(--accent2)' }}>intent → </span>{block.text}
        </div>
      )

    case 'plan':
      return (
        <div>
          <Divider label="PLAN" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {block.steps.map((step, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text2)' }}>
                <span style={{ color: 'var(--accent2)', flexShrink: 0, minWidth: 18 }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
      )

    case 'code':
      return (
        <div>
          <Divider label={block.retry ? `CODE (retry ${block.retry})` : 'GENERATED CODE'} />
          <div style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 8, overflow: 'hidden', fontFamily: 'var(--mono)',
          }}>
            <div style={{
              background: 'var(--surface2)', padding: '5px 12px',
              borderBottom: '1px solid var(--border)',
              display: 'flex', justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: 10, color: 'var(--text3)' }}>analysis.py</span>
              <span style={{ fontSize: 10, color: 'var(--amber)' }}>python</span>
            </div>
            <pre style={{
              padding: 12, fontSize: 11, color: 'var(--text2)',
              overflowX: 'auto', maxHeight: 280, overflowY: 'auto',
              lineHeight: 1.65, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {block.code}
            </pre>
          </div>
        </div>
      )

    case 'error':
      return (
        <div style={{
          background: 'rgba(248,113,113,0.07)',
          border: '1px solid rgba(248,113,113,0.25)',
          borderRadius: 8, padding: '10px 14px',
          fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--red)',
        }}>
          ⚠ Execution error{block.retry_count ? ` — retrying (attempt ${block.retry_count})` : ''}
          <pre style={{ marginTop: 6, fontSize: 10, color: 'var(--text3)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {block.error}
          </pre>
        </div>
      )

    case 'output':
      return block.text ? (
        <div>
          <Divider label="OUTPUT" />
          <pre style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 8, padding: 12,
            fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text2)',
            whiteSpace: 'pre-wrap', maxHeight: 220, overflowY: 'auto',
            wordBreak: 'break-word',
          }}>
            {block.text}
          </pre>
        </div>
      ) : null

    case 'chart':
      return (
        <div>
          <Divider label="CHART" />
          <div style={{
            background: 'var(--surface2)', border: '1px solid var(--border)',
            borderRadius: 10, overflow: 'hidden',
          }}>
            <iframe
              srcDoc={block.html}
              style={{
                width: '100%',
                height: 450,
                border: 'none',
                borderRadius: 10,
                display: 'block',
              }}
              sandbox="allow-scripts"
              title="Interactive Chart"
            />
          </div>
        </div>
      )

    case 'insights':
      return (
        <div>
          <Divider label="INSIGHTS" />
          <div style={{
            background: 'rgba(124,106,247,0.06)',
            border: '1px solid rgba(124,106,247,0.2)',
            borderRadius: 8, padding: '14px 16px',
            fontSize: 13, lineHeight: 1.75,
          }}>
            {block.text}
          </div>
        </div>
      )

    case 'patterns':
      return (
        <div>
          <Divider label="PATTERNS DETECTED" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {block.items.map((p, i) => (
              <div key={i} style={{
                background: 'rgba(245,158,11,0.06)',
                border: '1px solid rgba(245,158,11,0.25)',
                borderRadius: '8px',
                padding: '10px 14px',
              }}>
                <div style={{ fontSize: '12px', color: 'var(--amber)', marginBottom: '6px' }}>
                  ⚠ {p.alert}
                </div>
                {p.question && (
                  <button
                    onClick={() => window.dispatchEvent(new CustomEvent('suggestion', { detail: p.question }))}
                    style={{
                      background: 'rgba(245,158,11,0.08)',
                      border: '1px solid rgba(245,158,11,0.2)',
                      borderRadius: '6px',
                      padding: '5px 10px',
                      fontSize: '11px',
                      color: 'var(--amber)',
                      cursor: 'pointer',
                      fontFamily: 'var(--sans)',
                    }}
                  >
                    → {p.question}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )

    case 'suggestions':
      return (
        <div>
          <Divider label="SUGGESTED QUESTIONS" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {block.items.map((q, i) => (
              <button
                key={i}
                onClick={() => window.dispatchEvent(new CustomEvent('suggestion', { detail: q }))}
                style={{
                  background: 'rgba(124,106,247,0.06)',
                  border: '1px solid rgba(124,106,247,0.2)',
                  borderRadius: '8px',
                  padding: '8px 14px',
                  fontSize: '12px',
                  color: 'var(--text2)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontFamily: 'var(--sans)',
                  transition: 'background 0.2s',
                }}
                onMouseEnter={e => e.target.style.background = 'rgba(124,106,247,0.15)'}
                onMouseLeave={e => e.target.style.background = 'rgba(124,106,247,0.06)'}
              >
                <span style={{ color: 'var(--accent)', marginRight: '8px' }}>→</span>{q}
              </button>
            ))}
          </div>
        </div>
      )

    default:
      return null
  }
}

function Divider({ label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '4px 0 8px' }}>
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      <span style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--text3)', letterSpacing: '1px' }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
    </div>
  )
}

function Avatar({ color, children }) {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: 6,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 11, fontWeight: 700, flexShrink: 0,
      fontFamily: 'var(--mono)',
      background: `${color}22`,
      border: `1px solid ${color}44`,
      color,
    }}>
      {children}
    </div>
  )
}
