import { useState, useEffect, useRef } from 'react'

interface TimerRingProps {
  remaining: number
  total: number
  size?: number
}

export default function TimerRing({ remaining, total, size = 120 }: TimerRingProps) {
  const [display, setDisplay] = useState(remaining)
  const lastServer = useRef(remaining)
  const lastTs     = useRef(Date.now())
  const raf        = useRef<number | null>(null)

  useEffect(() => {
    lastServer.current = remaining
    lastTs.current = Date.now()
    setDisplay(remaining)
  }, [remaining])

  useEffect(() => {
    const tick = () => {
      const elapsed = (Date.now() - lastTs.current) / 1000
      setDisplay(Math.max(0, lastServer.current - elapsed))
      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [])

  const radius = (size - 14) / 2
  const circ   = 2 * Math.PI * radius
  const pct    = Math.max(0, Math.min(1, display / Math.max(total, 1)))
  const offset = circ * (1 - pct)

  const isUrgent  = display <= 10
  const isWarning = display <= 30 && !isUrgent
  const color = isUrgent ? '#FF3B5C' : isWarning ? '#FFD600' : '#00E5FF'
  const glowColor = isUrgent
    ? 'rgba(255,59,92,0.7)'
    : isWarning ? 'rgba(255,214,0,0.6)' : 'rgba(0,229,255,0.6)'

  const mins = Math.floor(display / 60)
  const secs = Math.floor(display % 60)
  const label = `${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`

  return (
    <div
      className={`relative inline-flex items-center justify-center ${isUrgent ? 'animate-timer-pulse' : ''}`}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        {/* Track */}
        <circle
          cx={size/2} cy={size/2} r={radius}
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={10}
        />
        {/* Progress */}
        <circle
          cx={size/2} cy={size/2} r={radius}
          fill="none" stroke={color} strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{
            transition: 'stroke-dashoffset 0.1s linear, stroke 0.4s ease',
            filter: `drop-shadow(0 0 6px ${glowColor})`,
          }}
        />
      </svg>
      <span
        className="absolute font-display font-black tabular-nums"
        style={{
          fontSize: size < 90 ? '0.8rem' : size < 120 ? '1rem' : '1.25rem',
          color,
          textShadow: `0 0 12px ${glowColor}`,
        }}
        aria-label={`${label} remaining`}
      >
        {label}
      </span>
    </div>
  )
}
