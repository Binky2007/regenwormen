// frontend/src/pages/Table.jsx
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useSocket } from '../context/SocketContext'
import { useGame } from '../context/GameContext'
import { playVictorySound } from '../lib/sound'
import { Confetti, Dancer } from '../components/Celebration'
import tableBg from '../assets/table-bg.jpg'

const PIPS = {
  1: [[50, 50]], 2: [[28, 28], [72, 72]], 3: [[26, 26], [50, 50], [74, 74]],
  4: [[30, 30], [70, 30], [30, 70], [70, 70]],
  5: [[30, 30], [70, 30], [50, 50], [30, 70], [70, 70]],
}
const wormsOn = n => (n <= 24 ? 1 : n <= 28 ? 2 : n <= 32 ? 3 : 4)
const val = f => (f === 'w' ? 5 : f)

const primaryBtn = { font: "900 13px 'Archivo', sans-serif", color: '#fff', background: '#a8232b', border: 0, borderBottom: '3px solid #7a1a20', borderRadius: 2, padding: '12px 18px', cursor: 'pointer' }
const mutedBtn = { font: "900 13px 'Archivo', sans-serif", color: '#1c1a14', background: '#ded7c5', border: '1px solid #b3ab99', borderRadius: 2, padding: '12px 18px', cursor: 'pointer' }
const resignBtn = { font: "900 12px 'Archivo', sans-serif", letterSpacing: '.1em', textTransform: 'uppercase', color: '#fff', background: '#a8232b', border: '1px solid #6f1319', borderRadius: 2, padding: '9px 14px', cursor: 'pointer' }
const overlayStyle = { position: 'fixed', inset: 0, zIndex: 60, background: 'rgba(10,7,4,.75)', display: 'grid', placeItems: 'center', padding: 20 }
const dialogStyle = { maxWidth: 400, width: '100%', padding: 28, borderRadius: 2, background: '#f4f0e6', border: '1px solid #c3bbaa' }

function Die({ face, live, onClick }) {
  const isWorm = face === 'w'
  return (
    <button onClick={onClick} disabled={!live} style={{
      position: 'relative', width: 48, height: 48, borderRadius: 9, background: '#fdfdfb',
      border: `1px solid ${live ? '#c2b7a3' : '#9a9182'}`, cursor: live ? 'pointer' : 'default',
      filter: live ? 'none' : 'grayscale(1) brightness(.72) contrast(.9)', padding: 0,
    }}>
      {isWorm
        ? <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4.5" strokeLinecap="round" /></svg>
        : PIPS[face].map(([x, y], i) => (
          <span key={i} style={{ position: 'absolute', width: 8, height: 8, borderRadius: 999, background: '#2b3a8f', left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }} />
        ))}
    </button>
  )
}

export default function Table() {
  const { user } = useAuth()
  const socket = useSocket()
  const { gameState: state, error, act, clearGame } = useGame()
  const navigate = useNavigate()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [starting, setStarting] = useState(false)
  const firedFanfareRef = useRef(false)

  useEffect(() => {
    if (state?.result && state.result.winner !== null) {
      if (!firedFanfareRef.current) {
        firedFanfareRef.current = true
        playVictorySound()
      }
    } else {
      firedFanfareRef.current = false
    }
  }, [state?.result])

  // A rematch keeps the opponent you just played: asking for another game
  // against a person must not quietly hand you the bot instead.
  function playAgain() {
    clearGame()
    if (state.mode === 'pvp') {
      navigate('/', { state: { autoMatch: true } })
      return
    }
    setStarting(true)
    socket.emit('start_bot_game')
  }

  if (!state) {
    if (starting) {
      return <div style={{ padding: 40, textAlign: 'center', color: '#54504a' }}>Setting up the table&hellip;</div>
    }
    // Landing here without a game (a stale link, a finished game cleared
    // away) used to wait forever on a game that was never coming.
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#54504a' }}>
        <p style={{ margin: '0 0 16px', fontSize: 15 }}>No game in progress.</p>
        <button onClick={() => navigate('/')} style={primaryBtn}>Back to the lobby</button>
      </div>
    )
  }

  const myIdx = user.id === state.player1_id ? 0 : 1
  const myTurn = state.turn === myIdx && !state.result
  const score = state.aside.reduce((t, f) => t + val(f), 0)
  const selectable = new Set(state.roll.filter(f => !state.aside.includes(f)))
  const canRoll = myTurn && state.roll.length === 0 && state.aside.length < 8
  const claimable = myTurn && state.roll.length === 0 && state.aside.length > 0
  const names = [state.player1_name, state.player2_name]
  const stacks = state.stacks

  function resign() {
    act('resign')
    setConfirmOpen(false)
  }

  return (
    <section style={{ flex: '1 1 auto', backgroundImage: `url(${tableBg})`, backgroundSize: 'cover', backgroundPosition: 'center', backgroundRepeat: 'no-repeat', padding: '18px 16px 30px' }}>
      <div style={{ maxWidth: 1080, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          {[0, 1].map(idx => {
            const stack = stacks[idx]
            const worms = stack.reduce((t, n) => t + wormsOn(n), 0)
            const active = state.turn === idx && !state.result
            const topTile = stack.length ? stack[stack.length - 1] : null
            const stealable = idx !== myIdx && claimable && topTile !== null && score === topTile && state.aside.includes('w')
            return (
              <div key={idx} style={{ flex: '1 1 220px', display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderRadius: 2, background: active ? 'rgba(255,255,255,.9)' : 'rgba(255,255,255,.62)', border: `1px solid ${active ? '#a8232b' : 'rgba(255,255,255,.35)'}` }}>
                <span style={{ width: 34, height: 34, borderRadius: 999, background: idx === 0 ? '#a8232b' : '#2b3a8f', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 13 }}>
                  {(names[idx] || '?').slice(0, 2).toUpperCase()}
                </span>
                <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                  <div style={{ fontWeight: 900, fontSize: 14, color: '#2a1c10', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {names[idx]}{idx === myIdx ? ' (you)' : ''}
                  </div>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#6b5541' }}>{stack.length} tiles &middot; {worms} worms{active ? ' · to move' : ''}</div>
                </div>
                {topTile !== null && (
                  <div
                    onClick={() => stealable && act('claim', { kind: 'steal', num: topTile })}
                    title={stealable ? `Click to steal tile ${topTile}` : `Top tile: ${topTile}`}
                    style={{
                      width: 44, padding: '9px 0 11px', borderRadius: 5, background: '#f7f1e1',
                      border: `2px solid ${stealable ? '#a8232b' : 'transparent'}`,
                      boxShadow: '0 2px 4px rgba(0,0,0,.3), inset 0 -2px 0 rgba(0,0,0,.08)',
                      textAlign: 'center', cursor: stealable ? 'pointer' : 'default',
                    }}
                  >
                    <div style={{ fontWeight: 900, fontSize: 16, color: '#1d2a4a' }}>{topTile}</div>
                    <div style={{ height: 1, background: '#1d2a4a', margin: '3px 7px' }} />
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 1, paddingTop: 3 }}>
                      {Array.from({ length: wormsOn(topTile) }).map((_, i) => (
                        <svg key={i} viewBox="0 0 24 24" width="9" height="9" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4.5" strokeLinecap="round" /></svg>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div style={{ padding: 14, borderRadius: 2, background: 'rgba(255,255,255,.14)', border: '1px solid rgba(255,255,255,.22)' }}>
          <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#4b3722', marginBottom: 10 }}>Tiles in the middle</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {Array.from({ length: 16 }, (_, i) => 21 + i).map(n => {
              const here = state.center.includes(n)
              const gone = state.out.includes(n)
              const maxTakeable = Math.max(-1, ...state.center.filter(c => c <= score))
              const pickable = claimable && score >= n && state.aside.includes('w') && here && n === maxTakeable
              return (
                <div key={n} onClick={() => pickable && act('claim', { kind: 'take', num: n })} style={{
                  width: 56, padding: '13px 0 15px', borderRadius: 6, textAlign: 'center',
                  background: here ? '#f7f1e1' : 'rgba(0,0,0,.13)',
                  border: `2px solid ${pickable ? '#3f7d4f' : 'transparent'}`,
                  opacity: gone ? 0.35 : 1, cursor: pickable ? 'pointer' : 'default',
                }}>
                  <div style={{ fontWeight: 900, fontSize: 21, color: here ? '#1d2a4a' : 'rgba(255,255,255,.35)' }}>{n}</div>
                  <div style={{ height: 1, background: here ? '#1d2a4a' : 'rgba(255,255,255,.22)', margin: '4px 9px' }} />
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 1, minHeight: 26, paddingTop: 4, flexWrap: 'wrap' }}>
                    {here && Array.from({ length: wormsOn(n) }).map((_, i) => (
                      <svg key={i} viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M5 19c0-7 6-4.5 6-10a3.2 3.2 0 016.4 0" fill="none" stroke="#a8232b" strokeWidth="4.5" strokeLinecap="round" /></svg>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
          <div style={{ padding: 16, borderRadius: 2, background: 'rgba(28,18,10,.5)', border: '1px solid rgba(255,255,255,.14)' }}>
            <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#d9b98e', marginBottom: 12 }}>
              Your roll &middot; {state.result ? 'game over' : myTurn ? (state.roll.length ? 'choose a value' : 'your move') : `${names[1 - myIdx]}’s turn`}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, minHeight: 56 }}>
              {state.roll.map((f, i) => (
                <Die key={i} face={f} live={myTurn && selectable.has(f)} onClick={() => act('pick', { face: f })} />
              ))}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 16 }}>
              {canRoll && <button onClick={() => act('roll')} style={primaryBtn}>Roll {8 - state.aside.length} dice</button>}
              {claimable && state.aside.length === 8 && <button onClick={() => act('stop')} style={mutedBtn}>Stop</button>}
              {!state.result && <button onClick={() => setConfirmOpen(true)} style={resignBtn}>Remise</button>}
            </div>
            {error && <div style={{ marginTop: 12, fontSize: 12, fontWeight: 700, color: '#e8a0a0' }}>{error}</div>}
          </div>

          <div style={{ padding: 16, borderRadius: 2, background: 'rgba(28,18,10,.5)', border: '1px solid rgba(255,255,255,.14)' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
              <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#d9b98e' }}>Set aside</div>
              <div style={{ fontWeight: 900, fontSize: 26, color: '#f7f1e1' }}>{score}</div>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, minHeight: 56 }}>
              {state.aside.map((f, i) => <Die key={i} face={f} live={false} onClick={() => {}} />)}
            </div>
            <div style={{ marginTop: 16, borderTop: '1px solid rgba(255,255,255,.12)', paddingTop: 12 }}>
              <div style={{ fontWeight: 900, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: '#d9b98e', marginBottom: 8 }}>Turn log</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 132, overflow: 'auto' }}>
                {state.log.map((line, i) => <div key={i} style={{ fontSize: 12, lineHeight: 1.4, color: '#bda98f' }}>{line.text}</div>)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {confirmOpen && (
        <div style={overlayStyle}>
          <div style={dialogStyle}>
            <h2 style={{ fontWeight: 900, fontSize: 22, margin: '0 0 8px', color: '#16150f' }}>Remise, resign this game?</h2>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: '#54504a', margin: '0 0 22px' }}>This game is scored as a loss. Your claimed tiles stay as they are.</p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={resign} style={{ ...resignBtn, flex: '1 1 130px' }}>Resign</button>
              <button onClick={() => setConfirmOpen(false)} style={{ ...mutedBtn, flex: '1 1 130px' }}>Keep playing</button>
            </div>
          </div>
        </div>
      )}

      {state.result && (
        <div style={overlayStyle}>
          {state.result.winner !== null && <Confetti />}
          <div style={{ ...dialogStyle, textAlign: 'center' }}>
            <h2 style={{ fontWeight: 900, fontSize: 28, margin: '0 0 10px', color: '#a8232b' }}>
              {state.result.winner === null ? 'Draw' : state.result.winner === myIdx ? 'You win!' : `${names[1 - myIdx]} wins`}
            </h2>
            {state.result.winner !== null && <Dancer />}
            <p style={{ fontSize: 15, lineHeight: 1.6, color: '#4a473f', margin: '0 0 24px' }}>
              Final count: {names[0]} {state.result.worms[0]} worms, {names[1]} {state.result.worms[1]} worms.
            </p>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={playAgain} style={{ ...primaryBtn, flex: '1 1 130px' }}>
                {state.mode === 'pvp' ? 'Find a new opponent' : 'Play again'}
              </button>
              <button onClick={() => navigate('/')} style={{ ...mutedBtn, flex: '1 1 130px' }}>Back to lobby</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
