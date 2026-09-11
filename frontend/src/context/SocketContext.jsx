// frontend/src/context/SocketContext.jsx
import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'
import { useAuth } from './AuthContext'

const SocketContext = createContext(null)

export function SocketProvider({ children }) {
  const { token } = useAuth()
  const [socket, setSocket] = useState(null)
  const ref = useRef(null)

  useEffect(() => {
    if (!token) {
      ref.current?.disconnect()
      ref.current = null
      setSocket(null)
      return
    }
    const s = io('/game', { auth: { token } })
    // On every connect -- first load, a refresh, a reconnect after the
    // backend restarted -- ask the server to put us back into whatever game
    // we are in. The server owns that answer, so we send no game id.
    const onConnect = () => s.emit('resume_game')
    s.on('connect', onConnect)
    ref.current = s
    setSocket(s)
    return () => { s.off('connect', onConnect); s.disconnect() }
  }, [token])

  return <SocketContext.Provider value={socket}>{children}</SocketContext.Provider>
}

export function useSocket() {
  return useContext(SocketContext)
}
