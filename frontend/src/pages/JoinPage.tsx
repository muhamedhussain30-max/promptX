import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import Logo from '@/components/shared/Logo'
import { gamesApi } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

export default function JoinPage() {
  const nav = useNavigate()
  const setPlayer = useAuthStore((s) => s.setPlayer)
  const [roomCode, setRoomCode] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(false)

  const join = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!roomCode.trim() || !displayName.trim()) return
    setLoading(true)
    try {
      const res = await gamesApi.join(roomCode.toUpperCase(), displayName.trim())
      setPlayer(res.session_token, res.player_id, res.display_name, res.game_id, res.room_code)
      toast.success(`Joined as ${res.display_name}!`)
      nav(`/lobby/${res.room_code}`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to join')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-900 px-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-sm">
        <div className="text-center mb-8"><Logo size="md" /></div>
        <div className="card p-8">
          <h2 className="text-2xl font-bold mb-6 text-center">Join a Room</h2>
          <form onSubmit={join} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Room Code</label>
              <input className="input text-center text-2xl font-mono tracking-[0.3em] uppercase"
                placeholder="X7K92P" maxLength={10} value={roomCode}
                onChange={e => setRoomCode(e.target.value.toUpperCase())} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Display Name</label>
              <input className="input" placeholder="Enter your name" maxLength={100}
                value={displayName} onChange={e => setDisplayName(e.target.value)} required />
            </div>
            <button type="submit" className="btn-primary w-full py-3 text-base" disabled={loading}>
              {loading ? 'Joining...' : '🎮 Join Game'}
            </button>
          </form>
          <p className="mt-4 text-center"><Link to="/" className="text-xs text-gray-500 hover:text-gray-400">← Back</Link></p>
        </div>
      </motion.div>
    </div>
  )
}
