// FileUpload.jsx
// Drag-and-drop / click-to-upload for CSV or JSON files.
// Calls POST /upload and returns the server's metadata via onUploaded().

import { useState, useRef } from 'react'

export default function FileUpload({ onUploaded }) {
  const [dragging, setDragging]   = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError]         = useState(null)
  const inputRef = useRef()

  async function handleFile(file) {
    if (!file) return
    if (!file.name.match(/\.(csv|json)$/i)) {
      setError('Only .csv and .json files are supported.')
      return
    }

    setUploading(true)
    setError(null)

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch('/upload', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Upload failed')
      onUploaded(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40, gap: 24 }}>
      <div style={{ fontSize: 40 }}>📊</div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontWeight: 800, fontSize: 22, marginBottom: 8 }}>
          Data Analyst Agent
        </div>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text3)', lineHeight: 1.7 }}>
          Upload a CSV or JSON file, then ask anything in plain English.<br/>
          The agent plans, writes code, executes it, and explains the results.
        </div>
      </div>

      {/* Drop zone */}
      <div
        onClick={() => !uploading && inputRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
        style={{
          border: `1.5px dashed ${dragging ? 'var(--accent)' : 'var(--border2)'}`,
          borderRadius: 12,
          padding: '32px 48px',
          textAlign: 'center',
          cursor: uploading ? 'wait' : 'pointer',
          background: dragging ? 'rgba(124,106,247,0.06)' : 'var(--surface2)',
          transition: 'all 0.2s',
          minWidth: 280,
        }}
      >
        <div style={{ fontSize: 28, marginBottom: 10 }}>{uploading ? '⏳' : '📂'}</div>
        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
          {uploading ? 'Uploading...' : 'Drop file here or click to browse'}
        </div>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text3)' }}>
          .csv or .json
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.json"
          style={{ display: 'none' }}
          onChange={e => handleFile(e.target.files[0])}
        />
      </div>

      {error && (
        <div style={{
          background: 'rgba(248,113,113,0.08)',
          border: '1px solid rgba(248,113,113,0.25)',
          borderRadius: 8, padding: '10px 16px',
          fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--red)',
        }}>
          ⚠ {error}
        </div>
      )}
    </div>
  )
}
