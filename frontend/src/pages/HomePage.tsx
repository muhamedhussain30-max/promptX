import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import Logo from '@/components/shared/Logo'

export default function HomePage() {
  const nav = useNavigate()
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-900 px-4">
      {/* Background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-brand-500/10 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative text-center max-w-2xl"
      >
        <Logo size="lg" />
        <p className="mt-4 text-xl text-gray-400 font-medium">
          Can you describe it without saying the obvious?
        </p>
        <p className="mt-2 text-gray-500">
          Generate AI images from prompts — without using forbidden keywords.
          The most accurate image wins.
        </p>

        <div className="mt-12 flex flex-col sm:flex-row gap-4 justify-center">
          <motion.button
            whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
            className="btn-primary text-lg px-10 py-4"
            onClick={() => nav('/join')}
          >
            🎮 Join a Game
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}
            className="btn-secondary text-lg px-10 py-4"
            onClick={() => nav('/host/login')}
          >
            🎯 Host a Contest
          </motion.button>
        </div>

        {/* Feature pills */}
        <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { icon: '👥', label: 'Up to 70 Players' },
            { icon: '⚡', label: 'Real-time' },
            { icon: '🖼️', label: 'AI Generated' },
            { icon: '🏆', label: 'Live Leaderboard' },
          ].map((f) => (
            <div key={f.label} className="card px-3 py-3 text-center">
              <div className="text-2xl">{f.icon}</div>
              <div className="text-xs text-gray-400 mt-1 font-medium">{f.label}</div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
