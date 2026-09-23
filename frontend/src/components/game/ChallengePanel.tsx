import { motion } from 'framer-motion'
import type { Challenge } from '@/types/game'

const diffMap: Record<string, string> = {
  EASY: 'badge-easy', MEDIUM: 'badge-medium',
  HARD: 'badge-hard', EXPERT: 'badge-expert',
}

export default function ChallengePanel({ challenge }: { challenge: Challenge }) {
  return (
    <div className="space-y-3">
      {/* Target */}
      <div className="card-cyan p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-heading font-semibold text-cyan-DEFAULT/70 uppercase tracking-widest">
            Target
          </span>
          <span className={diffMap[challenge.difficulty] ?? 'badge-medium'}>
            {challenge.difficulty}
          </span>
          <span className="badge" style={{ background: 'rgba(191,95,255,0.12)', color: '#BF5FFF', border: '1px solid rgba(191,95,255,0.3)' }}>
            {challenge.category}
          </span>
        </div>
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xl sm:text-2xl font-heading font-bold leading-snug text-white"
          style={{ textShadow: '0 0 24px rgba(0,229,255,0.15)' }}
        >
          "{challenge.target_description}"
        </motion.p>
      </div>

      {/* Forbidden words */}
      <div className="card-red p-4">
        <p className="text-xs font-heading font-semibold text-neon-red/80 uppercase tracking-widest mb-3">
          ⛔ Forbidden Words
        </p>
        <div className="flex flex-wrap gap-2">
          {challenge.forbidden_words.map((w) => (
            <motion.span
              key={w}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="forbidden-chip"
            >
              ⛔ {w}
            </motion.span>
          ))}
        </div>
        <p className="text-xs text-white/20 mt-3">
          Case-insensitive · word boundaries · no substitution tricks
        </p>
      </div>
    </div>
  )
}
