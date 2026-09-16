// frontend/src/pages/Lobby.jsx
import { useNavigate, useLocation } from 'react-router-dom'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useSocket } from '../context/SocketContext'
import { useGame } from '../context/GameContext'
import tilesImg from '../assets/regenwormen-tiles.png'
import lobbyBg from '../assets/lobby-bg.jpg'

const primaryBtn = { font: "900 14px 'Archivo', sans-serif", color: '#ffffff', background: '#a8232b', border: 0, borderBottom: '3px solid #7a1a20', borderRadius: 2, padding: '15px 22px', cursor: 'pointer' }
const secondaryBtn = { font: "900 14px 'Archivo', sans-serif", color: '#1c1a14', background: '#ded7c5', border: '1px solid #b3ab99', borderBottom: '3px solid #8e1c22', borderRadius: 2, padding: '15px 22px', cursor: 'pointer' }
const busy = { opacity: .6, cursor: 'progress' }

export default function Lobby() {
  const { user } = useAuth()
  const socket = useSocket()
  const { gameState, clearGame } = useGame()
  const navigate = useNavigate()
  const location = useLocation()

  // 'bot' or 'pvp' while we wait for the server to hand us a game, else null.
  // Mirrored into a ref so the unmount cleanup can read it without being
  // re-registered on every change.
  const [pending, setPendingState] = useState(null)
  const pendingRef = useRef(null)
  const setPending = useCallback(v => { pendingRef.current = v; setPendingState(v) }, [])

  // No `match_found` listener here on purpose. Lobby unmounts the moment the
  // user wanders off to any other page, and a listener that only exists on
  // this page misses the pairing entirely if the server matches them while
  // they are reading the rules. `game_state` is subscribed once, at Shell
  // level, in GameContext -- so we just watch for the game to show up.
  useEffect(() => {
    if (!pending || !gameState) return
    setPending(null)
    navigate('/table')
  }, [pending, gameState, navigate, setPending])

  // Leaving the lobby while queued would otherwise strand a ghost entry in
  // the matchmaking queue, ready to pair a player who is no longer waiting.
  useEffect(() => () => {
    if (pendingRef.current === 'pvp') socket?.emit('cancel_match')
  }, [socket])

  const playBot = useCallback(() => {
    if (!user) { navigate('/signed-out'); return }
    if (!socket || pending) return
    clearGame()
    setPending('bot')
    socket.emit('start_bot_game')
  }, [user, socket, pending, clearGame, setPending, navigate])

  const playOnline = useCallback(() => {
    if (!user) { navigate('/signed-out'); return }
    if (!socket || pending) return
    clearGame()
    setPending('pvp')
    socket.emit('find_match')
  }, [user, socket, pending, clearGame, setPending, navigate])

  // "Play again" after a PvP game sends the player back here asking for
  // another opponent, rather than quietly dropping them against the bot.
  const autoMatch = location.state?.autoMatch
  useEffect(() => {
    if (!autoMatch || !socket) return
    navigate('/', { replace: true, state: null })
    playOnline()
  }, [autoMatch, socket, navigate, playOnline])

  const resumable = gameState && !gameState.result && !pending

  return (
    <section style={{ flex: '1 1 auto', backgroundImage: `url(${lobbyBg})`, backgroundSize: 'cover', backgroundPosition: 'center', backgroundRepeat: 'no-repeat' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 28, alignItems: 'center', maxWidth: 1120, width: '100%', margin: '0 auto', padding: '40px 20px 56px' }}>
      <div style={{ background: 'rgba(244,240,230,.88)', borderRadius: 4, padding: '24px 26px' }}>
        <div style={{ fontWeight: 900, fontSize: 12, letterSpacing: '.18em', textTransform: 'uppercase', color: '#a8232b' }}>Two players &middot; eight dice &middot; sixteen tiles</div>
        <h1 style={{ fontWeight: 900, letterSpacing: '-.015em', fontSize: 'clamp(34px, 6vw, 58px)', lineHeight: 1.02, margin: '12px 0 14px', color: '#16150f' }}>Regenwormen in the browser</h1>
        <p style={{ fontSize: 16, lineHeight: 1.6, color: '#4a473f', maxWidth: '46ch', margin: '0 0 26px' }}>Set dice aside, stop in time, and claim the tile that matches your score. Play the bot, or wait for someone online to sit down.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          <button onClick={playBot} disabled={!!pending} style={pending ? { ...primaryBtn, ...busy } : primaryBtn}>
            {pending === 'bot' ? 'Dealing the tiles…' : 'Play the bot'}
          </button>
          <button onClick={playOnline} disabled={!!pending} style={pending ? { ...secondaryBtn, ...busy } : secondaryBtn}>Find an opponent</button>
        </div>
        {resumable && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 20, fontWeight: 600, fontSize: 13, color: '#4a473f' }}>
            You have a game in progress.
            <button onClick={() => navigate('/table')} style={{ background: 'none', border: 0, color: '#a8232b', textDecoration: 'underline', cursor: 'pointer', font: "700 13px 'Archivo', sans-serif" }}>
              Back to the table
            </button>
          </div>
        )}
        {pending === 'pvp' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 20, fontWeight: 600, fontSize: 13, color: '#a8232b' }}>
            <span style={{ width: 15, height: 15, border: '2px solid #b3ab99', borderTopColor: '#a8232b', borderRadius: 999, display: 'inline-block', animation: 'rw-spin .8s linear infinite' }} />
            Looking for an opponent
            <button onClick={() => { socket.emit('cancel_match'); setPending(null) }} style={{ background: 'none', border: 0, color: '#6d6961', textDecoration: 'underline', cursor: 'pointer', font: "600 13px 'Archivo', sans-serif" }}>
              Cancel
            </button>
          </div>
        )}
      </div>
      <div style={{ borderRadius: 2, overflow: 'hidden', border: '1px solid #c9c2b1' }}>
        <img src={tilesImg} alt="Regenwormen tiles and dice on a table" style={{ display: 'block', width: '100%', height: 'auto' }} />
      </div>
      </div>
    </section>
  )
}
