// frontend/src/pages/SignedOut.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const inputStyle = { width: '100%', padding: '11px 12px', marginBottom: 10, border: '1px solid #c3bbaa', borderRadius: 2, font: "400 14px 'Archivo', sans-serif" }

export default function SignedOut() {
  const { login, signup } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      if (mode === 'login') await login(email, password)
      else await signup(email, password, displayName)
      navigate('/')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section style={{ flex: '1 1 auto', display: 'grid', placeItems: 'center', padding: '60px 20px' }}>
      <form onSubmit={submit} style={{ maxWidth: 360, width: '100%', textAlign: 'center', padding: '34px 26px', borderRadius: 2, background: '#f4f0e6', border: '1px solid #ded7c5' }}>
        <h1 style={{ fontWeight: 900, fontSize: 26, margin: '0 0 8px', color: '#16150f' }}>{mode === 'login' ? 'Sign in' : 'Create account'}</h1>
        <p style={{ fontSize: 15, lineHeight: 1.6, color: '#54504a', margin: '0 0 22px' }}>Sign in to keep playing.</p>
        {mode === 'signup' && (
          <input value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder="Display name" required style={inputStyle} />
        )}
        <input value={email} onChange={e => setEmail(e.target.value)} type="email" placeholder="Email" required style={inputStyle} />
        <input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="Password" required style={inputStyle} />
        {error && <div style={{ color: '#a8232b', fontSize: 13, marginBottom: 12 }}>{error}</div>}
        <button type="submit" style={{ width: '100%', font: "900 14px 'Archivo', sans-serif", color: '#ffffff', background: '#a8232b', border: 0, borderBottom: '3px solid #7a1a20', borderRadius: 2, padding: '14px 20px', cursor: 'pointer' }}>
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </button>
        <button type="button" onClick={() => setMode(m => m === 'login' ? 'signup' : 'login')} style={{ marginTop: 12, background: 'none', border: 0, color: '#a8232b', cursor: 'pointer', font: "700 13px 'Archivo', sans-serif" }}>
          {mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Sign in'}
        </button>
      </form>
    </section>
  )
}
