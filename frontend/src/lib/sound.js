// Drop a legally-obtained track at frontend/public/sounds/victory.mp3 to use
// it instead — synthesized fallback fires only when that file is missing.
export function playVictorySound() {
  const audio = new Audio('/sounds/victory.mp3')
  audio.volume = 1
  audio.play().catch(() => playVictoryFanfare())
  setTimeout(() => { audio.pause(); audio.currentTime = 0 }, 5000)
}

export function playVictoryFanfare() {
  const Ctx = window.AudioContext || window.webkitAudioContext
  if (!Ctx) return
  const ctx = new Ctx()
  const notes = [523.25, 659.25, 783.99, 1046.50] // C5 E5 G5 C6
  const noteDuration = 0.16

  notes.forEach((freq, i) => {
    const start = ctx.currentTime + i * noteDuration
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'triangle'
    osc.frequency.value = freq
    gain.gain.setValueAtTime(0, start)
    gain.gain.linearRampToValueAtTime(1, start + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.001, start + noteDuration)
    osc.connect(gain).connect(ctx.destination)
    osc.start(start)
    osc.stop(start + noteDuration)
  })

  const closeAt = notes.length * noteDuration * 1000 + 100
  setTimeout(() => ctx.close(), closeAt)
}
