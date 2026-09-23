import { motion, AnimatePresence } from 'framer-motion'
import type { LeaderboardEntry } from '@/types/game'

const MEDALS: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }

function rankColor(rank: number): string {
  if (rank === 1) return '#FFD600'
  if (rank === 2) return '#A0A0B0'
  if (rank === 3) return '#FF8C00'
  return 'rgba(255,255,255,0.3)'
}

export default function LeaderboardTable({
  entries,
  highlightPlayerId,
  showAdvancement = false,
}: {
  entries: LeaderboardEntry[]
  highlightPlayerId?: string
  showAdvancement?: boolean
}) {
  return (
    <div className="space-y-1.5">
      <AnimatePresence mode="popLayout">
        {entries.map((e, i) => {
          const isMe        = e.player_id === highlightPlayerId
          const isAdvanced  = e.is_advanced === true
          const isEliminated = e.is_advanced === false
          const color       = rankColor(e.rank)

          return (
            <motion.div
              key={e.player_id}
              layout
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: isEliminated ? 0.4 : 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              transition={{ delay: i * 0.03, duration: 0.25 }}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                isMe ? 'border border-cyan-DEFAULT/35' : 'border border-white/4'
              }`}
              style={{
                background: isMe
                  ? 'rgba(0,229,255,0.06)'
                  : 'rgba(255,255,255,0.02)',
              }}
            >
              {/* Rank */}
              <span className="w-8 text-center font-display font-black text-base flex-shrink-0"
                    style={{ color }}>
                {MEDALS[e.rank] ?? `#${e.rank}`}
              </span>

              {/* Avatar */}
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                   style={{
                     background: isAdvanced ? 'rgba(57,255,154,0.15)' :
                                 isEliminated ? 'rgba(255,255,255,0.04)' :
                                 'rgba(0,229,255,0.10)',
                     color: isAdvanced ? '#39FF9A' : isEliminated ? '#555' : '#00E5FF',
                     border: `1px solid ${isAdvanced ? 'rgba(57,255,154,0.25)' :
                               isEliminated ? 'rgba(255,255,255,0.06)' :
                               'rgba(0,229,255,0.20)'}`,
                   }}>
                {e.display_name[0].toUpperCase()}
              </div>

              {/* Name */}
              <div className="flex-1 min-w-0">
                <p className="font-heading font-semibold text-sm text-white/80 truncate">
                  {e.display_name}
                  {isMe && <span className="ml-1.5 text-xs text-cyan-DEFAULT/50">(you)</span>}
                </p>
                <p className="text-xs text-white/25 font-mono">
                  acc {e.accuracy * 2} · spd {e.speed * 10}
                </p>
              </div>

              {/* Score */}
              <div className="text-right flex-shrink-0">
                <p className="font-display font-black text-lg" style={{ color: '#FFD600' }}>
                  {e.round_score}
                </p>
                <p className="text-xs text-white/25 font-mono">{e.cumulative_score} total</p>
              </div>

              {/* Advancement */}
              {showAdvancement && e.is_advanced !== null && (
                <span className={`text-xs font-heading font-bold px-2 py-0.5 rounded-lg flex-shrink-0 ${
                  isAdvanced
                    ? 'bg-neon-green/10 text-neon-green border border-neon-green/25'
                    : 'bg-neon-red/10 text-neon-red border border-neon-red/25'
                }`}>
                  {isAdvanced ? '✓' : '✗'}
                </span>
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
