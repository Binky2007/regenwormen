// frontend/src/pages/Profile.jsx
import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

export default function Profile() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  useEffect(() => { api.profile().then(setStats).catch(() => setStats(null)) }, [])

  const initials = (user?.display_name || '?').slice(0, 2).toUpperCase()
  const cards = stats ? [
    { value: stats.games, label: 'Games played' },
    { value: stats.worms, label: 'Worms won' },
    { value: `${stats.win_rate}%`, label: 'Win rate' },
    { value: stats.best_turn, label: 'Best single turn' },
  ] : []

  return (
    <section style={{ maxWidth: 720, margin: '0 auto', padding: '44px 20px 70px', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 30 }}>
        <span style={{ width: 64, height: 64, borderRadius: 999, background: '#a8232b', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 22 }}>{initials}</span>
        <div>
          <h1 style={{ fontWeight: 900, fontSize: 30, margin: 0, color: '#16150f' }}>{user?.display_name}</h1>
          <div style={{ fontSize: 14, color: '#6d6961' }}>{user?.email}</div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
        {cards.map(c => (
          <div key={c.label} style={{ padding: 18, borderRadius: 2, background: '#f4f0e6', border: '1px solid #ded7c5' }}>
            <div style={{ fontWeight: 900, fontSize: 28, color: '#a8232b' }}>{c.value}</div>
            <div style={{ fontSize: 12, letterSpacing: '.1em', textTransform: 'uppercase', color: '#6d6961', marginTop: 4 }}>{c.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
