import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import Logo from '@/components/shared/Logo'
import ConnectionStatus from '@/components/shared/ConnectionStatus'
import TimerRing from '@/components/shared/TimerRing'
import LeaderboardTable from '@/components/leaderboard/LeaderboardTable'
import { useGameStore } from '@/stores/gameStore'
import { useAuthStore } from '@/stores/authStore'
import { useGameWebSocket } from '@/hooks/useGameWebSocket'
import wsService from '@/services/websocket'
import { gamesApi } from '@/services/api'
import type { Player } from '@/types/game'

export default function HostDashboardPage() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const nav = useNavigate()
  const auth = useAuthStore()
  const store = useGameStore()
  const [advancing, setAdvancing] = useState(40)

  const token = auth.hostToken ?? ''
  // Always call hooks — guard after
  useGameWebSocket({ roomCode: roomCode!, token, isHost: true })

  // Redirect if not host — AFTER hooks
  useEffect(() => {
    if (!auth.isHost()) nav('/host/login')
  }, [auth, nav])

  const activeCount = store.players.filter(p => p.status !== 'ELIMINATED').length
  const submittedCount = store.players.filter(p => p.status === 'SUBMITTED').length
  const totalScore = store.leaderboard.length > 0
    ? Math.round(store.leaderboard.reduce((s, e) => s + e.round_score, 0) / store.leaderboard.length)
    : 0
  const topPlayer = store.leaderboard[0]

  const statCards = [
    { label: 'Active Players',   value: activeCount,   total: store.maxPlayers,   icon: '👥' },
    { label: 'Current Round',    value: store.currentRound?.round_number ?? 0, total: store.totalRounds, icon: '🔄' },
    { label: 'Submitted',        value: submittedCount, total: activeCount,        icon: '✅' },
    { label: 'Avg Score',        value: totalScore,     total: 100,                icon: '📊' },
  ]

  return (
    <div className="min-h-screen bg-surface-900 flex flex-col">
      <header className="border-b border-surface-600 px-6 py-4 flex items-center justify-between">
        <Logo size="sm" />
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">
            Host: <span className="text-white font-medium">{auth.hostDisplayName}</span>
          </span>
          <ConnectionStatus />
        </div>
      </header>

      <div className="max-w-7xl mx-auto w-full px-4 py-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {statCards.map((s) => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500 uppercase tracking-wider">{s.label}</span>
                <span className="text-xl">{s.icon}</span>
              </div>
              <div className="text-3xl font-black text-white">{s.value}</div>
              <div className="text-sm text-gray-500">of {s.total}</div>
            </motion.div>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Timer + Controls */}
          <div className="space-y-4">
            {/* Timer */}
            {store.currentRound && (
              <div className="card p-6 text-center">
                <p className="text-xs text-gray-500 uppercase tracking-widest mb-3">Round Timer</p>
                <TimerRing remaining={store.remainingSeconds} total={store.roundDuration} size={140} />
                {topPlayer && (
                  <div className="mt-4 text-sm text-gray-400">
                    Top: <span className="text-white font-semibold">{topPlayer.display_name}</span>
                    <span className="text-accent-yellow ml-2">{topPlayer.round_score}</span>
                  </div>
                )}
              </div>
            )}

            {/* Controls */}
            <div className="card p-6 space-y-3">
              <h3 className="font-semibold text-gray-300 text-sm uppercase tracking-wider">Controls</h3>

              {store.gameStatus === 'LOBBY' && (
                <button onClick={() => wsService.send('host_start_game', {})}
                  disabled={store.players.length === 0}
                  className="btn-primary w-full py-3">
                  🚀 Start Game
                </button>
              )}
              {store.gameStatus === 'ROUND_ACTIVE' && (
                <button onClick={() => wsService.send('host_end_round', {})} className="btn-danger w-full py-3">
                  ⏹ End Round Early
                </button>
              )}
              {(store.gameStatus === 'LEADERBOARD') && (
                <>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">Players advancing</label>
                    <input type="number" className="input" value={advancing} min={1} max={activeCount}
                      onChange={e => setAdvancing(Number(e.target.value))} />
                  </div>
                  <button onClick={() => wsService.send('host_shortlist', { advancing_count: advancing })}
                    className="btn-secondary w-full py-3">
                    ⚡ Apply Shortlist
                  </button>
                  <button onClick={() => wsService.send('host_next_round', {})} className="btn-primary w-full py-3">
                    ▶ Next Round
                  </button>
                </>
              )}
              {store.gameStatus === 'SHORTLISTING' && (
                <button onClick={() => wsService.send('host_next_round', {})} className="btn-primary w-full py-3">
                  ▶ Start Next Round
                </button>
              )}
              <button onClick={() => wsService.send('host_end_game', {})} className="btn-danger w-full py-2 text-sm">
                🏁 End Contest
              </button>
            </div>

            {/* Game status */}
            <div className="card p-4 text-center">
              <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">Game Status</p>
              <p className="font-mono font-bold text-brand-400 text-lg">{store.gameStatus}</p>
            </div>
          </div>

          {/* Player list */}
          <div className="card p-4">
            <h3 className="font-semibold text-gray-300 text-sm uppercase tracking-wider mb-3">
              Players ({store.players.length}/{store.maxPlayers})
            </h3>
            <div className="space-y-1.5 max-h-[500px] overflow-y-auto pr-1">
              {store.players.map((p: Player) => (
                <div key={p.id}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg ${
                    p.status === 'ELIMINATED' ? 'opacity-40 bg-surface-700' : 'bg-surface-700 hover:bg-surface-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      p.status === 'ACTIVE' ? 'bg-accent-green' :
                      p.status === 'SUBMITTED' ? 'bg-brand-400' :
                      p.status === 'ELIMINATED' ? 'bg-gray-600' : 'bg-gray-500'
                    }`} />
                    <span className="text-sm font-medium truncate max-w-[120px]">{p.display_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">{p.total_score}</span>
                    <button
                      className="text-xs text-accent-red/60 hover:text-accent-red px-1"
                      onClick={() => wsService.send('host_remove_player', { player_id: p.id })}
                    >✕</button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Live leaderboard */}
          <div className="card p-4">
            <h3 className="font-semibold text-gray-300 text-sm uppercase tracking-wider mb-3">
              Live Leaderboard
            </h3>
            {store.leaderboard.length > 0 ? (
              <div className="max-h-[500px] overflow-y-auto pr-1">
                <LeaderboardTable entries={store.leaderboard.slice(0, 20)} />
              </div>
            ) : (
              <p className="text-gray-500 text-sm text-center py-8">Round results will appear here</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
