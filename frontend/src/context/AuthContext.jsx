// frontend/src/context/AuthContext.jsx
import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('rw_token'))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) { setLoading(false); return }
    api.me()
      .then(setUser)
      .catch(() => { setToken(null); localStorage.removeItem('rw_token') })
      .finally(() => setLoading(false))
  }, [token])

  const login = useCallback(async (email, password) => {
    const { token: t, user: u } = await api.login({ email, password })
    localStorage.setItem('rw_token', t)
    setToken(t)
    setUser(u)
  }, [])

  const signup = useCallback(async (email, password, display_name) => {
    const { token: t, user: u } = await api.signup({ email, password, display_name })
    localStorage.setItem('rw_token', t)
    setToken(t)
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('rw_token')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
