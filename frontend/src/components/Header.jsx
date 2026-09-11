// frontend/src/components/Header.jsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navLinkStyle = {
  font: "700 13px 'Archivo', sans-serif", color: '#1c1a14', background: 'transparent',
  border: '1px solid transparent', borderRadius: 2, padding: '8px 12px',
  cursor: 'pointer', textDecoration: 'none',
}

export default function Header() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const initials = (user?.display_name || 'G').slice(0, 2).toUpperCase()

  const menuItems = [
    { label: 'Profile / stats', act: () => { setOpen(false); navigate('/profile') } },
    { label: 'Help & rules', act: () => { setOpen(false); navigate('/rules') } },
    { label: 'Log out', act: () => { setOpen(false); logout(); navigate('/signed-out') } },
  ]

  return (
    <header style={{ position: 'sticky', top: 0, zIndex: 40, display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', padding: '10px 18px', background: '#f4f0e6', borderBottom: '1px solid #c9c2b1' }}>
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', color: 'inherit', flex: '0 0 auto' }}>
        <div style={{ width: 34, height: 34, borderRadius: 2, background: '#16150f', display: 'grid', placeItems: 'center' }}>
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4" strokeLinecap="round" /></svg>
        </div>
        <span style={{ fontWeight: 900, letterSpacing: '.3px', fontSize: 19, color: '#16150f' }}>Regenwormen</span>
      </Link>

      <nav style={{ display: 'flex', alignItems: 'center', gap: 4, flex: '1 1 auto', flexWrap: 'wrap' }}>
        {/* The lobby, not the table: /table only ever shows a game that has
            already been started, so this is where a new game begins. */}
        <Link to="/" style={navLinkStyle}>New game</Link>
        <Link to="/rules" style={navLinkStyle}>Game rules</Link>
        <Link to="/leaderboard" style={navLinkStyle}>Leaderboard</Link>
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: '0 0 auto' }}>
        {user ? (
          <div style={{ position: 'relative' }}>
            <button onClick={() => setOpen(o => !o)} style={{ display: 'flex', alignItems: 'center', gap: 9, background: '#ded7c5', border: '1px solid #c3bbaa', borderRadius: 999, padding: '5px 12px 5px 5px', cursor: 'pointer', color: '#1c1a14' }}>
              <span style={{ width: 28, height: 28, borderRadius: 999, background: '#a8232b', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 12 }}>{initials}</span>
              <span style={{ fontWeight: 700, fontSize: 13 }}>{user.display_name}</span>
              <span style={{ fontSize: 10, opacity: .7 }}>&#9662;</span>
            </button>
            {open && (
              <div style={{ position: 'absolute', right: 0, top: 'calc(100% + 8px)', width: 232, background: '#f4f0e6', border: '1px solid #c3bbaa', borderRadius: 2, padding: 8 }}>
                <div style={{ padding: '8px 10px 10px', borderBottom: '1px solid #ded7c5', marginBottom: 6 }}>
                  <div style={{ fontWeight: 900, fontSize: 14 }}>{user.display_name}</div>
                  <div style={{ fontSize: 12, color: '#54504a' }}>{user.email}</div>
                </div>
                {menuItems.map(item => (
                  <button key={item.label} onClick={item.act} style={{ width: '100%', textAlign: 'left', background: 'transparent', border: 0, borderRadius: 2, padding: '9px 10px', color: '#1c1a14', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <Link to="/signed-out" style={{ ...navLinkStyle, background: '#a8232b', color: '#fff' }}>Sign in</Link>
        )}
      </div>
    </header>
  )
}
