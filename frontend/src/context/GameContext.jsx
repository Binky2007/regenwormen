// frontend/src/context/GameContext.jsx
import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useSocket } from './SocketContext'

const GameContext = createContext(null)

export function GameProvider({ children }) {
  const socket = useSocket()
  const [gameState, setGameState] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!socket) { setGameState(null); return }
    const onState = (s) => { setGameState(s); setError(null) }
    const onError = (e) => setError(e.message)
    socket.on('game_state', onState)
    socket.on('error', onError)
    return () => {
      socket.off('game_state', onState)
      socket.off('error', onError)
    }
  }, [socket])

  const act = useCallback((type, payload) => {
    if (!socket || !gameState) return
    socket.emit('action', { game_id: gameState.game_id, type, payload })
  }, [socket, gameState])

  // Drop the board before asking for a new game, so the finished one does
  // not flash (or linger, if the request never lands) in its place.
  const clearGame = useCallback(() => { setGameState(null); setError(null) }, [])

  return (
    <GameContext.Provider value={{ gameState, error, act, clearGame }}>
      {children}
    </GameContext.Provider>
  )
}

export function useGame() {
  return useContext(GameContext)
}
