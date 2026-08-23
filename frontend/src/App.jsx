import React, { useEffect, useState } from 'react'

export default function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch(setError)
  }, [])

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 640, margin: '4rem auto', padding: '0 1rem' }}>
      <h1>TregoCon</h1>
      <p>Tabletop gaming weekend — lodging, meals &amp; games.</p>
      <h2>API health</h2>
      {error && <pre style={{ color: 'crimson' }}>Error: {String(error)}</pre>}
      {health && <pre style={{ background: '#f4f4f4', padding: '1rem', borderRadius: 8 }}>{JSON.stringify(health, null, 2)}</pre>}
      {!health && !error && <p>Checking…</p>}
    </main>
  )
}
