// ChatWindow.jsx
// Renders the conversation: user messages, agent thinking steps,
// generated code, charts (as images from the backend), and insights.

import { useEffect, useRef } from 'react'

export default function ChatWindow({ messages }) {
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
    }}>
      {messages.length === 0 && (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          color: 'var(--text3)',
          textAlign: 'center',
          padding: '60px 20px',
        }}>
          <div style={{ fontSize: '40px' }}>⬡</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text2)' }}>
            Ready to analyze
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', maxWidth: '300px', lineHeight: 1.7 }}>
            Upload a CSV or JSON file, then ask anything in natural language.
          </div>
        </div>
      )}

      {messages.map((msg, i) => (
        <Message key={i} msg={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}


function Message({ msg }) {
  if (msg.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', animation: 'fadeUp 0.3s ease' }}>
        <div style={{
          maxWidth: '70%',
          background: 'rgba(124,106,247,0.12)',
          border: '1px solid rgba(124,106,247,0.25)',
          borderRadius: '10px 10px 3px 10px',
          padding: '12px 16px',
          fontSize: '13px',
          lineHeight: 1.65,
        }}>
          {msg.text}
        </div>
        <div style={avatarStyle('#7c6af7')}>U</div>
      </div>
    )
  }

  // Agent message — can contain multiple blocks
  return (
    <div style={{ display: 'flex', gap: '10px', animation: 'fadeUp 0.3s ease' }}>
      <div style={avatarStyle('#2dd4bf')}>⬡</div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '85%' }}>
        {msg.blocks?.map((block, i) => <Block key={i} block={block} />)}
      </div>
    </div>
  )
}

function Block({ block }) {
  switch (block.type) {
    case 'intent':
      return (
        <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text3)', paddingLeft: '4px' }}>
          <span style={{ color: 'var(--accent2)' }}>intent: </span>{block.text}
        </div>
      )

    case 'plan':
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <Divider label="PLAN" />
          {block.steps.map((step, i) => (
            <div key={i} style={{
              fontFamily: 'var(--mono)',
              fontSize: '11px',
              color: 'var(--text2)',
              display: 'flex',
              gap: '8px',
            }}>
              <span style={{ color: 'var(--accent2)', flexShrink: 0, minWidth: '18px' }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <span>{step}</span>
            </div>
          ))}
        </div>
      )

    case 'code':
      return (
        <div>
          <Divider label={block.retry ? `GENERATED CODE (retry ${block.retry})` : 'GENERATED CODE'} />
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            overflow: 'hidden',
            fontFamily: 'var(--mono)',
          }}>
            <div style={{
              background: 'var(--surface2)',
              padding: '6px 12px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: '10px', color: 'var(--text3)' }}>analysis.py</span>
              <span style={{ fontSize: '10px', color: 'var(--amber)' }}>python</span>
            </div>
            <pre style={{
              padding: '12px',
              fontSize: '11px',
              color: 'var(--text2)',
              overflowX: 'auto',
              maxHeight: '260px',
              overflowY: 'auto',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}>
              {block.code}
            </pre>
          </div>
        </div>
      )

    case 'error':
      return (
        <div style={{
          background: 'rgba(248,113,113,0.08)',
          border: '1px solid rgba(248,113,113,0.25)',
          borderRadius: '8px',
          padding: '10px 14px',
          fontFamily: 'var(--mono)',
          fontSize: '11px',
          color: 'var(--red)',
        }}>
          ⚠ Execution error (retrying...)<br/>
          <span style={{ color: 'var(--text3)', fontSize: '10px' }}>{block.error}</span>
        </div>
      )

    case 'output':
      return block.text ? (
        <div>
          <Divider label="OUTPUT" />
          <pre style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '12px',
            fontFamily: 'var(--mono)',
            fontSize: '11px',
            color: 'var(--text2)',
            whiteSpace: 'pre-wrap',
            maxHeight: '200px',
            overflowY: 'auto',
          }}>
            {block.text}
          </pre>
        </div>
      ) : null

    case 'chart':
      return (
        <div>
          <Divider label="VISUALIZATION" />
          <div style={{
            background: 'var(--surface2)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            overflow: 'hidden',
          }}>
            <iframe
              srcDoc={block.html}
              style={{
                width: '100%',
                height: '450px',
                border: 'none',
                borderRadius: '10px',
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
            borderRadius: '8px',
            padding: '14px 16px',
            fontSize: '13px',
            lineHeight: 1.75,
          }}>
            {block.text}
          </div>
        </div>
      )

    default:
      return null
  }
}

function Divider({ label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '6px 0' }}>
      <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
      <span style={{ fontFamily: 'var(--mono)', fontSize: '9px', color: 'var(--text3)', letterSpacing: '1px' }}>
        {label}
      </span>
      <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
    </div>
  )
}

function avatarStyle(color) {
  return {
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: 700,
    flexShrink: 0,
    fontFamily: 'var(--mono)',
    background: `${color}22`,
    border: `1px solid ${color}44`,
    color: color,
  }
}
