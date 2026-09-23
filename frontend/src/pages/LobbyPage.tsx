import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Logo from '@/components/shared/Logo'
import ConnectionStatus from '@/components/shared/ConnectionStatus'
import { useGameStore } from '@/stores/gameStore'
import { useAuthStore } from '@/stores/authStore'
import { useGameWebSocket } from '@/hooks/useGameWebSocket'
import { playersApi } from '@/services/api'
import { toast } from 'react-hot-toast'
import wsService from '@/services/websocket'
import type { Player } from '@/types/game'

export default function LobbyPage() {
  const { roomCode } = useParams<{ roomCode: string }>()
  const nav   = useNavigate()
  const auth  = useAuthStore()
  const store = useGameStore()

  const token  = auth.playerToken ?? auth.hostToken ?? ''
  const isHost = !auth.playerToken && auth.isHost()

  useGameWebSocket({ roomCode: roomCode!, token, isHost })

  useEffect(() => {
    if (['ROUND_ACTIVE', 'COUNTDOWN', 'ROUND_PROCESSING'].includes(store.gameStatus)) {
      nav(isHost ? `/host/dashboard/${roomCode}` : `/game/${roomCode}`)
    }
    if (store.gameStatus === 'FINISHED') nav(`/results/${roomCode}`)
  }, [store.gameStatus, roomCode, nav, isHost])

  const [isReady, setIsReady]   = useState(false)
  const [loading, setLoading]   = useState(false)

  useEffect(() => {
    const me = store.players.find(p => p.id === auth.playerId)
    if (me) setIsReady(me.is_ready)
  }, [store.players, auth.playerId])

  const toggleReady = async () => {
    if (isHost || loading) return
    const next = !isReady
    setIsReady(next)
    setLoading(true)
    try { await playersApi.setReady(next) }
    catch { setIsReady(!next); toast.error('Failed to update ready state') }
    finally { setLoading(false) }
  }

  const readyCount = store.players.filter(p => p.is_ready).length
  const allReady   = store.players.length > 0 && store.players.every(p => p.is_ready)
  const fillPct    = store.maxPlayers > 0
    ? Math.round((store.players.length / store.maxPlayers) * 100) : 0

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-6 py-4 flex items-center justify-between border-b border-cyan-DEFAULT/10"
              style={{ background: 'rgba(11,11,20,0.92)', backdropFilter: 'blur(16px)' }}>
        <Logo size="sm" />
        <ConnectionStatus />
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8 space-y-5">

        {/* Room info card */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}
          className="card-cyan p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl font-black text-white mb-1">{store.gameTitle}</h1>
              <p className="text-white/40 text-sm font-heading">
                {store.totalRounds} rounds · {store.roundDuration}s each · {store.maxAttempts} attempts
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs font-heading text-white/30 uppercase tracking-widest mb-1">Room Code</p>
              <p className="font-display text-3xl font-black text-neon-cyan glow-text tracking-widest">
                {roomCode}
              </p>
            </div>
          </div>

          {/* Fill bar */}
          <div className="mt-5">
            <div className="flex justify-between text-xs font-heading text-white/40 mb-1.5">
              <span>Players</span>
              <span>{store.players.length} / {store.maxPlayers}</span>
            </div>
            <div className="h-2 rounded-full overflow-hidden"
                 style={{ background: 'rgba(255,255,255,0.06)' }}>
              <motion.div
                className="h-full rounded-full"
                style={{ background: 'linear-gradient(90deg,#00E5FF,#BF5FFF)',
                         boxShadow: '0 0 12px rgba(0,229,255,0.4)' }}
                initial={{ width: 0 }}
                animate={{ width: `${fillPct}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-5">

          {/* Player list */}
          <div className="md:col-span-2 card p-4">
            <h2 className="font-heading text-xs font-semibold text-white/40 uppercase tracking-widest mb-3">
              Players — {readyCount}/{store.players.length} ready
            </h2>
            <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
              <AnimatePresence>
                {store.players.map((p: Player) => (
                  <motion.div
                    key={p.id}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 12 }}
                    className={`flex items-center justify-between px-3 py-2.5 rounded-xl transition-all ${
                      p.id === auth.playerId
                        ? 'border border-cyan-DEFAULT/30 bg-cyan-DEFAULT/5'
                        : 'border border-white/5 bg-white/2'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                        p.is_ready
                          ? 'bg-neon-green/20 text-neon-green border border-neon-green/30'
                          : 'bg-white/5 text-white/30 border border-white/10'
                      }`}>
                        {p.display_name[0].toUpperCase()}
                      </div>
                      <span className="font-heading font-medium text-sm text-white/80">
                        {p.display_name}
                        {p.id === auth.playerId && (
                          <span className="ml-2 text-xs text-cyan-DEFAULT/60">(you)</span>
                        )}
                      </span>
                    </div>
                    <span className={`text-xs font-heading font-bold ${
                      p.is_ready ? 'text-neon-green' : 'text-white/20'
                    }`}>
                      {p.is_ready ? '✓ READY' : 'waiting…'}
                    </span>
                  </motion.div>
                ))}
              </AnimatePresence>
              {store.players.length === 0 && (
                <p className="text-center text-white/20 py-8 text-sm font-heading">
                  Waiting for players to join…
                </p>
              )}
            </div>
          </div>

          {/* Action panel */}
          <div className="card p-5 flex flex-col gap-4">
            <div className="text-center">
              <div className="text-3xl mb-1">{isHost ? '🎯' : '🎮'}</div>
              <p className="font-heading font-semibold text-sm text-white/60">
                {isHost ? 'Host Controls' : 'Player Panel'}
              </p>
            </div>

            {!isHost && (
              <button
                onClick={toggleReady}
                disabled={loading}
                className={`btn w-full py-3 text-sm font-heading font-bold ${
                  isReady
                    ? 'border border-neon-green/40 bg-neon-green/10 text-neon-green'
                    : 'btn-cyan'
                }`}
              >
                {loading ? '…' : isReady ? '✓ Ready! (click to unready)' : 'Mark as Ready'}
              </button>
            )}

            {isHost && (
              <>
                <p className={`text-xs text-center font-heading ${
                  allReady ? 'text-neon-green' : 'text-white/40'
                }`}>
                  {allReady ? '✅ All players ready!' : `${readyCount}/${store.players.length} ready`}
                </p>
                <button
                  disabled={store.players.length === 0}
                  onClick={() => wsService.send('host_start_game', {})}
                  className="btn-cyan w-full py-3 text-sm font-heading font-bold"
                >
                  🚀 START GAME
                </button>
              </>
            )}

            <p className="text-xs text-white/20 text-center border-t border-white/5 pt-3 font-heading">
              Share the room code with contestants
            </p>
          </div>
        </div>
      </main>

      {/* Countdown overlay */}
      <AnimatePresence>
        {store.gameStatus === 'COUNTDOWN' && store.countdownValue !== null && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: 'rgba(11,11,20,0.92)', backdropFilter: 'blur(12px)' }}
          >
            <motion.div
              key={store.countdownValue}
              initial={{ scale: 1.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.7, opacity: 0 }}
              className="text-center"
            >
              <p className="font-display text-9xl font-black text-neon-cyan"
                 style={{ textShadow: '0 0 60px rgba(0,229,255,0.9)' }}>
                {store.countdownValue}
              </p>
              <p className="font-heading text-xl font-semibold text-white/60 mt-4">GET READY!</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
