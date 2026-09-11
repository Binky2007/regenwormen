// frontend/src/components/Celebration.jsx
const CONFETTI_COLORS = ['#a8232b', '#2b3a8f', '#d9b98e', '#3f7d4f', '#f2c14e']

export function Confetti() {
  const pieces = Array.from({ length: 40 }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    delay: Math.random() * 0.6,
    duration: 2 + Math.random() * 1.2,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
    rotate: Math.random() * 360,
  }))

  return (
    <>
      <style>{`
        @keyframes confetti-fall {
          0% { transform: translateY(-10vh) rotate(0deg); opacity: 1; }
          100% { transform: translateY(110vh) rotate(720deg); opacity: .9; }
        }
      `}</style>
      <div style={{ position: 'fixed', inset: 0, zIndex: 70, pointerEvents: 'none', overflow: 'hidden' }} aria-hidden="true">
        {pieces.map(p => (
          <span key={p.id} style={{
            position: 'absolute', top: 0, left: `${p.left}%`, width: 8, height: 14,
            background: p.color, transform: `rotate(${p.rotate}deg)`,
            animation: `confetti-fall ${p.duration}s ease-in ${p.delay}s 1 forwards`,
          }} />
        ))}
      </div>
    </>
  )
}

export function Dancer() {
  return (
    <>
      <style>{`
        @keyframes dancer-wiggle {
          0%, 100% { transform: rotate(-18deg) translateY(0); }
          50% { transform: rotate(18deg) translateY(-6px); }
        }
      `}</style>
      <div style={{ fontSize: 40, margin: '4px 0 14px', animation: 'dancer-wiggle .6s ease-in-out infinite' }} aria-hidden="true">
        💃
      </div>
    </>
  )
}
