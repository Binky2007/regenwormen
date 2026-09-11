// frontend/src/pages/Leaderboard.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Leaderboard() {
  const [rows, setRows] = useState([])
  useEffect(() => { api.leaderboard().then(setRows).catch(() => setRows([])) }, [])

  return (
    <section style={{ maxWidth: 720, margin: '0 auto', padding: '44px 20px 70px', width: '100%' }}>
      <h1 style={{ fontWeight: 900, fontSize: 'clamp(28px, 5vw, 42px)', margin: '0 0 6px', color: '#16150f' }}>Leaderboard</h1>
      <p style={{ fontSize: 15, color: '#6d6961', margin: '0 0 26px' }}>Worms collected this season.</p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {rows.map(row => (
          <div key={row.rank} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '13px 16px', borderRadius: 2, background: '#f4f0e6', border: '1px solid #ded7c5' }}>
            <span style={{ fontWeight: 900, fontSize: 15, color: '#a8232b', width: 26 }}>{row.rank}</span>
            <span style={{ flex: '1 1 auto', fontWeight: 700, fontSize: 15, color: '#1c1a14' }}>{row.name}</span>
            <span style={{ fontSize: 13, color: '#6d6961' }}>{row.games} games</span>
            <span style={{ fontWeight: 900, fontSize: 15, color: '#a8232b', width: 46, textAlign: 'right' }}>{row.worms}</span>
          </div>
        ))}
        {rows.length === 0 && <p style={{ color: '#6d6961', fontSize: 14 }}>No games played yet — be the first to claim a tile.</p>}
      </div>
    </section>
  )
}
