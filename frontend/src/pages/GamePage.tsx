import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Logo from '@/components/shared/Logo'
import ConnectionStatus from '@/components/shared/ConnectionStatus'
import TimerRing from '@/components/shared/TimerRing'
import ChallengePanel from '@/components/game/ChallengePanel'
import PromptEditor from '@/components/game/PromptEditor'
import { useGameStore } from '@/stores/gameStore'
import { useAuthStore } from '@/stores/authStore'
import { useGameWebSocket } from '@/hooks/useGameWebSocket'

export default function GamePage() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const nav  = useNavigate()
  const auth = useAuthStore()
  const store = useGameStore()

  const token  = auth.playerToken ?? auth.hostToken ?? ''
  const isHost = !auth.playerToken && auth.isHost()

  useGameWebSocket({ roomCode: roomCode!, token, isHost })

  useEffect(() => {
    if (['LEADERBOARD', 'SHORTLISTING', 'FINISHED'].includes(store.gameStatus)) {
      nav(`/results/${roomCode}`)
    }
  }, [store.gameStatus, roomCode, nav])

  const round        = store.currentRound
  const isRoundActive = store.gameStatus === 'ROUND_ACTIVE'
  const isProcessing  = store.gameStatus === 'ROUND_PROCESSING'
  const attemptsUsed  = store.submissions.length

  const handleGenerate = (submissionId: string) => {
    store.setCurrentSubmissionId(submissionId)
    store.setIsGenerating(true)
  }

  if (!round) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-14 h-14 rounded-full border-2 border-cyan-DEFAULT/30 border-t-cyan-DEFAULT
                          animate-spin mx-auto" />
          <p className="text-white/50 font-heading">Loading round…</p>
          <button onClick={() => nav(`/lobby/${roomCode}`)}
            className="text-xs text-cyan-DEFAULT/60 hover:text-cyan-DEFAULT underline">
            Return to lobby
          </button>
        </div>
      </div>
    )
  }

  const myScore = store.myScore

  return (
    <div className="min-h-screen flex flex-col">

      {/* ── Top bar ───────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 px-4 sm:px-6 py-3 flex items-center gap-4
                         border-b border-cyan-DEFAULT/10"
              style={{ background: 'rgba(11,11,20,0.92)', backdropFilter: 'blur(16px)' }}>
        {/* Left — logo + round */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <Logo size="sm" />
          <div className="hidden sm:flex items-center gap-2 text-sm font-heading">
            <span className="text-white/30">Round</span>
            <span className="text-neon-cyan font-bold">{round.round_number}</span>
            <span className="text-white/20">/</span>
            <span className="text-white/40">{round.total_rounds}</span>
          </div>
        </div>

        {/* Center — timer (prominent) */}
        <div className="flex-shrink-0">
          <TimerRing remaining={store.remainingSeconds} total={round.duration} size={80} />
        </div>

        {/* Right — score + connection */}
        <div className="flex items-center gap-3 flex-1 justify-end">
          {auth.playerId && (
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-xs text-white/30 font-heading uppercase tracking-widest">Score</span>
              <span className="text-lg font-display font-bold text-neon-yellow"
                    style={{ textShadow: '0 0 10px rgba(255,214,0,0.5)' }}>
                {store.players.find(p => p.id === auth.playerId)?.total_score ?? 0}
              </span>
            </div>
          )}
          <ConnectionStatus />
        </div>
      </header>

      {/* ── Scoring overlay ───────────────────────────────────────────────── */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: 'rgba(11,11,20,0.88)', backdropFilter: 'blur(8px)' }}>
            <div className="card-cyan p-10 text-center max-w-sm">
              <div className="w-16 h-16 rounded-full border-2 border-cyan-DEFAULT/30 border-t-cyan-DEFAULT
                              animate-spin mx-auto mb-6" />
              <h2 className="font-display text-2xl font-bold text-neon-cyan mb-2">Evaluating</h2>
              <p className="text-white/50">Analysing images and calculating scores…</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main — two-column on desktop, stacked on mobile ─────────────── */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-5">

        {/* Mobile timer (shown above content on small screens) */}
        <div className="flex sm:hidden justify-center mb-4">
          <TimerRing remaining={store.remainingSeconds} total={round.duration} size={100} />
        </div>

        {/* Grid: left = challenge, right = prompt editor */}
        <div className="grid lg:grid-cols-2 gap-5">

          {/* ── Left ─────────────────────────────────────────────────────── */}
          <div className="space-y-4 order-2 lg:order-1">
            <ChallengePanel challenge={round.challenge} />

            {/* Generated image preview */}
            <AnimatePresence>
              {store.generatedImageUrl && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="card-cyan overflow-hidden"
                >
                  <p className="text-xs font-heading text-cyan-DEFAULT/60 uppercase tracking-widest px-4 pt-3 pb-1">
                    Generated Image
                  </p>
                  <img src={store.generatedImageUrl} alt="Generated"
                       className="w-full object-cover" style={{ maxHeight: 280 }} />
                  <div className="px-4 py-2 text-xs text-neon-green font-heading font-semibold"
                       style={{ background: 'rgba(57,255,154,0.07)' }}>
                    ✓ Submitted automatically
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Generating shimmer */}
            {store.isGenerating && !store.generatedImageUrl && (
              <div className="card overflow-hidden">
                <p className="text-xs font-heading text-white/30 uppercase tracking-widest px-4 pt-3 pb-1">
                  Generating…
                </p>
                <div className="shimmer-box w-full" style={{ height: 220 }} />
                <div className="px-4 py-3 text-xs text-white/40 font-heading">
                  Will submit automatically when ready
                </div>
              </div>
            )}
          </div>

          {/* ── Right ────────────────────────────────────────────────────── */}
          <div className="space-y-4 order-1 lg:order-2">
            {isRoundActive ? (
              <PromptEditor
                roundId={round.round_id}
                forbiddenWords={round.challenge.forbidden_words}
                maxAttempts={store.maxAttempts}
                attemptsUsed={attemptsUsed}
                onGenerate={handleGenerate}
                disabled={!isRoundActive}
              />
            ) : (
              <div className="card p-8 text-center">
                <div className="text-5xl mb-4">⏰</div>
                <h3 className="font-heading text-xl font-bold mb-2">Time's Up!</h3>
                <p className="text-white/40">Scores are being calculated…</p>
              </div>
            )}

            {/* Inline score flash (brief, before redirect to results) */}
            {myScore && (
              <AnimatedScorePanel score={myScore} />
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

/* ── Inline score bars (briefly visible before redirect) ─────────────────── */
function AnimatedScorePanel({ score }: { score: any }) {
  const rows = [
    { label: 'Image Match',  value: score?.match_score  ?? score?.accuracy * 2 ?? 0,         color: '#00E5FF' },
    { label: 'Creativity',   value: score?.creativity_100 ?? score?.creativity * 10 ?? 0,     color: '#BF5FFF' },
    { label: 'Speed',        value: score?.speed_100    ?? score?.speed * 10 ?? 0,             color: '#39FF9A' },
    { label: 'Efficiency',   value: score?.efficiency_100 ?? score?.efficiency * 10 ?? 0,     color: '#FFD600' },
  ]
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
      <h3 className="font-heading font-semibold text-white/70 text-sm uppercase tracking-widest mb-3">
        Your Score
      </h3>
      {rows.map(({ label, value, color }, i) => (
        <div key={label} className="mb-2.5">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-white/50">{label}</span>
            <span className="font-mono font-bold" style={{ color }}>{value}</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <motion.div
              className="h-full rounded-full"
              style={{ background: color, boxShadow: `0 0 8px ${color}` }}
              initial={{ width: 0 }}
              animate={{ width: `${value}%` }}
              transition={{ duration: 0.8, delay: i * 0.12, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
        </div>
      ))}
      <div className="mt-3 pt-3 flex justify-between items-center"
           style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}>
        <span className="text-white/40 font-heading text-sm">Final Score</span>
        <motion.span
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.6, type: 'spring', stiffness: 200 }}
          className="font-display text-2xl font-black text-neon-yellow"
          style={{ textShadow: '0 0 16px rgba(255,214,0,0.6)' }}
        >
          {score?.total ?? 0}
        </motion.span>
      </div>
    </motion.div>
  )
}
