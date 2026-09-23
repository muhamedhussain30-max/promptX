import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Logo from '@/components/shared/Logo'
import ConnectionStatus from '@/components/shared/ConnectionStatus'
import LeaderboardTable from '@/components/leaderboard/LeaderboardTable'
import { useGameStore } from '@/stores/gameStore'
import { useAuthStore } from '@/stores/authStore'
import { useGameWebSocket } from '@/hooks/useGameWebSocket'
import wsService from '@/services/websocket'
import type { ConceptResult, ScoreBreakdown } from '@/types/game'

// ── Count-up hook ─────────────────────────────────────────────────────────────
function useCountUp(target: number, duration = 1400, delay = 600) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (target === 0) { setVal(0); return }
    const start = Date.now() + delay
    const tick = () => {
      const now = Date.now()
      if (now < start) { requestAnimationFrame(tick); return }
      const elapsed = now - start
      const pct = Math.min(elapsed / duration, 1)
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - pct, 3)
      setVal(Math.round(eased * target))
      if (pct < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [target, duration, delay])
  return val
}

// ── Score bar with animation ──────────────────────────────────────────────────
function ScoreBar({ label, value, max = 100, color, delay = 0 }: {
  label: string; value: number; max?: number; color: string; delay?: number
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1.5">
        <span className="text-white/50 font-heading">{label}</span>
        <span className="font-mono font-bold" style={{ color }}>{value}<span className="text-white/25">/{max}</span></span>
      </div>
      <div className="h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 8px ${color}66` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.9, delay, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  )
}

// ── Final score ring ──────────────────────────────────────────────────────────
function ScoreRing({ score }: { score: number }) {
  const displayed = useCountUp(score, 1200, 400)
  const size = 156
  const r    = 58
  const circ = 2 * Math.PI * r
  const color = score >= 70 ? '#39FF9A' : score >= 45 ? '#FFD600' : '#FF3B5C'
  const glow  = score >= 70 ? 'rgba(57,255,154,0.7)' : score >= 45 ? 'rgba(255,214,0,0.6)' : 'rgba(255,59,92,0.7)'

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size/2} cy={size/2} r={r} fill="none"
                stroke="rgba(255,255,255,0.06)" strokeWidth={12} />
        <motion.circle
          cx={size/2} cy={size/2} r={r} fill="none"
          stroke={color} strokeWidth={12} strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ * (1 - score / 100) }}
          transition={{ duration: 1.3, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          style={{ filter: `drop-shadow(0 0 8px ${glow})` }}
        />
      </svg>
      <div className="absolute text-center">
        <motion.span
          className="font-display font-black text-4xl block"
          style={{ color, textShadow: `0 0 20px ${glow}` }}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, type: 'spring', stiffness: 200 }}
        >
          {displayed}
        </motion.span>
        <span className="text-xs text-white/30 font-mono">/100</span>
      </div>
    </div>
  )
}

// ── Concept badge ──────────────────────────────────────────────────────────────
function ConceptBadge({ cr }: { cr: ConceptResult }) {
  const { icon, color, bg, border } = {
    yes:     { icon: '✓', color: '#39FF9A', bg: 'rgba(57,255,154,0.10)',  border: 'rgba(57,255,154,0.30)' },
    partial: { icon: '~', color: '#FFD600', bg: 'rgba(255,214,0,0.10)',   border: 'rgba(255,214,0,0.30)' },
    no:      { icon: '✗', color: '#FF3B5C', bg: 'rgba(255,59,92,0.10)',   border: 'rgba(255,59,92,0.30)' },
  }[cr.result] ?? { icon: '?', color: '#ffffff', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.12)' }

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-heading font-medium"
         style={{ background: bg, border: `1px solid ${border}`, color }}>
      <span className="font-bold text-base w-4 text-center" style={{ textShadow: `0 0 8px ${color}` }}>
        {icon}
      </span>
      <span className="flex-1">{cr.label}</span>
      <span className="text-xs opacity-60 capitalize">{cr.result}</span>
    </div>
  )
}

// ── Player score panel ────────────────────────────────────────────────────────
function PlayerScorePanel({ score }: { score: ScoreBreakdown }) {
  const concepts = score.accuracy_breakdown?.concepts ?? []
  const m        = score.match_score ?? 0

  const explanation =
    m >= 80 ? 'Excellent image match — the AI nailed it!' :
    m >= 60 ? 'Good match — most elements visible.' :
    m >= 40 ? 'Partial match — some elements missing.' :
    m >= 20 ? 'Weak match — key elements not visible.' :
              'Image did not match. Score capped at 20.'

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">

      {/* Image */}
      {score.image_url && (
        <div className="card-cyan overflow-hidden">
          <img src={score.image_url} alt="Your generated image"
               className="w-full object-cover" style={{ maxHeight: 260 }} />
          {score.raw_prompt && (
            <div className="px-4 py-3 border-t border-cyan-DEFAULT/10">
              <p className="text-xs text-white/30 font-heading uppercase tracking-widest mb-1">Prompt</p>
              <p className="text-sm text-white/60 italic">"{score.raw_prompt}"</p>
            </div>
          )}
        </div>
      )}

      {/* Final score + explanation */}
      <div className="card p-5 flex flex-col sm:flex-row items-center gap-5">
        <ScoreRing score={score.total} />
        <div className="flex-1">
          <h3 className="font-heading font-bold text-white/80 text-base mb-1">Final Score</h3>
          <p className="text-sm text-white/40 leading-relaxed">{explanation}</p>
          {m < 20 && (
            <span className="mt-2 inline-block text-xs font-heading font-bold text-neon-red
                             bg-neon-red/10 border border-neon-red/25 rounded-lg px-2 py-0.5">
              Capped — image match below 20
            </span>
          )}
        </div>
      </div>

      {/* Score bars */}
      <div className="card p-5">
        <h3 className="font-heading text-xs font-semibold text-white/30 uppercase tracking-widest mb-4">
          Breakdown
        </h3>
        <ScoreBar label="Image Match"  value={score.match_score    ?? 0} color="#00E5FF" delay={0.0} />
        <ScoreBar label="Creativity"   value={score.creativity_100 ?? 0} color="#BF5FFF" delay={0.1} />
        <ScoreBar label="Speed"        value={score.speed_100      ?? 0} color="#39FF9A" delay={0.2} />
        <ScoreBar label="Efficiency"   value={score.efficiency_100 ?? 0} color="#FFD600" delay={0.3} />
      </div>

      {/* Vision sub-scores */}
      {(score.subject_score > 0 || score.scene_score > 0) && (
        <div className="card p-5">
          <h3 className="font-heading text-xs font-semibold text-white/30 uppercase tracking-widest mb-4">
            Image Analysis
          </h3>
          <ScoreBar label="Subject accuracy"  value={score.subject_score     ?? 0} color="#00E5FF" delay={0.0} />
          <ScoreBar label="Scene accuracy"    value={score.scene_score       ?? 0} color="#06d6a0" delay={0.1} />
          <ScoreBar label="Composition"       value={score.composition_score ?? 0} color="#BF5FFF" delay={0.2} />
          <ScoreBar label="Concept coverage"  value={score.concept_coverage  ?? 0} color="#ff9f1c" delay={0.3} />
        </div>
      )}

      {/* Concept checklist */}
      {concepts.length > 0 && (
        <div className="card p-5">
          <h3 className="font-heading text-xs font-semibold text-white/30 uppercase tracking-widest mb-4">
            Element Checklist
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <AnimatePresence>
              {concepts.map((cr, i) => (
                <motion.div
                  key={`${cr.label}-${i}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 * i }}
                >
                  <ConceptBadge cr={cr} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          <div className="mt-3 pt-3 flex gap-4 text-xs text-white/20 font-heading"
               style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <span><span className="text-neon-green font-bold">✓</span> Clearly visible</span>
            <span><span className="text-neon-yellow font-bold">~</span> Partially shown</span>
            <span><span className="text-neon-red font-bold">✗</span> Not found</span>
          </div>
        </div>
      )}
    </motion.div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ResultsPage() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const nav   = useNavigate()
  const auth  = useAuthStore()
  const store = useGameStore()

  const token  = auth.playerToken ?? auth.hostToken ?? ''
  const isHost = !auth.playerToken && auth.isHost()

  useGameWebSocket({ roomCode: roomCode!, token, isHost })

  useEffect(() => {
    if (['ROUND_ACTIVE', 'COUNTDOWN', 'NEXT_ROUND'].includes(store.gameStatus)) {
      nav(`/game/${roomCode}`)
    }
  }, [store.gameStatus, roomCode, nav])

  const isShortlisting = store.gameStatus === 'SHORTLISTING'
  const isFinished     = store.gameStatus === 'FINISHED'
  const myEntry        = store.leaderboard.find(e => e.player_id === auth.playerId)
  const myShortlist    = [...store.shortlistAdvanced, ...store.shortlistEliminated]
    .find(e => e.player_id === auth.playerId)

  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-6 py-4 flex items-center justify-between border-b border-cyan-DEFAULT/10"
              style={{ background: 'rgba(11,11,20,0.92)', backdropFilter: 'blur(16px)' }}>
        <Logo size="sm" />
        <div className="flex items-center gap-4">
          {isFinished && (
            <span className="font-display text-sm text-neon-yellow glow-text tracking-widest">
              CONTEST COMPLETE
            </span>
          )}
          <ConnectionStatus />
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8">

        {/* Title */}
        <motion.div initial={{ opacity: 0, y: -14 }} animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8">
          {isFinished ? (
            <>
              <p className="text-5xl mb-3">🏆</p>
              <h1 className="font-display text-4xl font-black text-gradient-gold">CONTEST COMPLETE</h1>
            </>
          ) : (
            <>
              <p className="text-4xl mb-2">📊</p>
              <h1 className="font-heading text-3xl font-black text-white">
                Round {store.currentRound?.round_number} Results
              </h1>
            </>
          )}
        </motion.div>

        <div className="grid lg:grid-cols-5 gap-6">

          {/* ── Score panel (left, wider) ─────────────────────────────────── */}
          {!isHost && store.myScore && (
            <div className="lg:col-span-3 space-y-4">
              <PlayerScorePanel score={store.myScore} />
              <motion.button
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }}
                onClick={() => nav('/')}
                className="btn-ghost w-full py-3 font-heading font-semibold"
              >
                🔄 Play Again
              </motion.button>
            </div>
          )}

          {/* ── Leaderboard (right) ───────────────────────────────────────── */}
          <div className={`${(!isHost && store.myScore) ? 'lg:col-span-2' : 'lg:col-span-5'} space-y-4`}>

            {/* My rank banner */}
            <AnimatePresence>
              {myEntry && !isHost && (
                <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
                  className={`card p-4 grid grid-cols-3 gap-3 ${
                    myShortlist?.is_advanced === false ? 'border-neon-red/40' :
                    myShortlist?.is_advanced === true  ? 'border-neon-green/40' :
                    'border-cyan-DEFAULT/20'
                  }`}
                  style={{ border: '1px solid' }}
                >
                  {[
                    { label: 'Rank',  val: `#${myEntry.rank}`,             color: '#FFD600' },
                    { label: 'Round', val: String(myEntry.round_score),     color: '#00E5FF' },
                    { label: 'Total', val: String(myEntry.cumulative_score),color: '#BF5FFF' },
                  ].map(({ label, val, color }) => (
                    <div key={label} className="text-center">
                      <p className="text-xs text-white/30 font-heading mb-0.5">{label}</p>
                      <p className="font-display text-2xl font-black" style={{ color }}>{val}</p>
                    </div>
                  ))}
                  {myShortlist && (
                    <div className={`col-span-3 text-center text-sm font-heading font-bold pt-2
                                    border-t border-white/5 ${
                      myShortlist.is_advanced ? 'text-neon-green' : 'text-neon-red'
                    }`}>
                      {myShortlist.is_advanced ? '✓ ADVANCING' : '✗ ELIMINATED'}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Leaderboard */}
            <div className="card p-4">
              <h2 className="font-heading text-xs font-semibold text-white/30 uppercase tracking-widest mb-3">
                🏆 Leaderboard {store.leaderboard.length > 0 && (
                  <span className="text-white/20 normal-case font-normal ml-1">
                    ({store.leaderboard.length})
                  </span>
                )}
              </h2>
              {store.leaderboard.length > 0 ? (
                <div className="max-h-[480px] overflow-y-auto">
                  <LeaderboardTable
                    entries={store.leaderboard}
                    highlightPlayerId={auth.playerId ?? undefined}
                    showAdvancement={isShortlisting || isFinished}
                  />
                </div>
              ) : (
                <div className="py-10 text-center text-white/25">
                  <div className="w-7 h-7 border-2 border-white/10 border-t-cyan-DEFAULT/50
                                  rounded-full animate-spin mx-auto mb-3" />
                  <p className="font-heading text-sm">Calculating…</p>
                </div>
              )}
            </div>

            {/* Host controls */}
            {isHost && !isFinished && (
              <div className="card p-5 space-y-3">
                <h3 className="font-heading text-xs font-semibold text-white/30 uppercase tracking-widest">
                  Host Controls
                </h3>
                <div className="flex flex-wrap gap-2">
                  {!isShortlisting && (
                    <>
                      <button className="btn-ghost text-sm py-2 px-4"
                        onClick={() => wsService.send('host_shortlist', {
                          advancing_count: Math.ceil(store.leaderboard.length / 2)
                        })}>
                        ⚡ Top 50%
                      </button>
                      <button className="btn-ghost text-sm py-2 px-4"
                        onClick={() => wsService.send('host_shortlist', {
                          advancing_count: Math.min(40, store.leaderboard.length)
                        })}>
                        ⚡ Top 40
                      </button>
                    </>
                  )}
                  {(isShortlisting || store.gameStatus === 'LEADERBOARD') && (
                    <button className="btn-cyan text-sm py-2 px-4"
                      onClick={() => wsService.send('host_next_round', {})}>
                      ▶ Next Round
                    </button>
                  )}
                  <button className="btn-danger text-sm py-2 px-4"
                    onClick={() => wsService.send('host_end_game', {})}>
                    🏁 End Contest
                  </button>
                </div>
              </div>
            )}

            {/* Play again */}
            {(isHost || !store.myScore) && (
              <motion.button
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
                onClick={() => nav('/')}
                className="btn-ghost w-full py-3 font-heading font-semibold"
              >
                🔄 {isFinished ? 'New Contest' : 'Play Again'}
              </motion.button>
            )}
          </div>
        </div>

        {/* Winner podium */}
        {isFinished && store.leaderboard.length >= 1 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }} className="card-cyan p-8 mt-8">
            <h2 className="font-display text-2xl font-black text-center text-gradient-gold mb-8">
              🏆 Final Podium
            </h2>
            <div className="flex items-end justify-center gap-6">
              {[
                { rank: 2, h: 'h-24', w: 'w-20', color: '#A0A0B0', border: 'rgba(160,160,176,0.3)' },
                { rank: 1, h: 'h-32', w: 'w-24', color: '#FFD600', border: 'rgba(255,214,0,0.5)' },
                { rank: 3, h: 'h-20', w: 'w-20', color: '#FF8C00', border: 'rgba(255,140,0,0.3)' },
              ].map(({ rank, h, w, color, border }) => {
                const entry = store.leaderboard[rank - 1]
                if (!entry) return null
                return (
                  <div key={rank} className="text-center">
                    {rank === 1 && <p className="text-3xl mb-2">👑</p>}
                    <div className={`${w} ${h} rounded-t-xl flex items-end justify-center pb-2`}
                         style={{ background: `${color}15`, border: `2px solid ${border}` }}>
                      <span className="font-display text-3xl font-black" style={{ color }}>{rank}</span>
                    </div>
                    <div className="mt-2">
                      <p className="font-heading font-bold text-sm text-white/80">{entry.display_name}</p>
                      <p className="font-display font-black text-lg" style={{ color }}>{entry.cumulative_score}</p>
                    </div>
                  </div>
                )
              })}
            </div>
            <div className="text-center mt-8">
              <button onClick={() => nav('/')}
                className="btn-cyan px-10 py-3 text-base font-display tracking-wider">
                🎮 Play Again
              </button>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  )
}
