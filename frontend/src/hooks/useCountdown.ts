/**
 * useCountdown — derives a live countdown display from the server-provided end time.
 * Does NOT use its own setInterval for the authoritative time — it reads from the
 * store which is updated by server timer_updated events.
 */
import { useGameStore } from '@/stores/gameStore'

export function useCountdown() {
  const remaining = useGameStore((s) => s.remainingSeconds)
  const minutes = Math.floor(remaining / 60)
  const seconds = Math.floor(remaining % 60)
  const formatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  const pct = remaining  // caller knows total duration from store
  const isUrgent = remaining <= 10 && remaining > 0
  const isExpired = remaining <= 0

  return { remaining, minutes, seconds, formatted, isUrgent, isExpired }
}
