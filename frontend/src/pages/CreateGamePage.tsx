import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import Logo from '@/components/shared/Logo'
import { gamesApi } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

export default function CreateGamePage() {
  const nav = useNavigate()
  const { isHost } = useAuthStore()
  const [form, setForm] = useState({
    title: 'PromptX Prelims', max_players: 70,
    total_rounds: 5, round_duration: 600, max_attempts: 3,
  })
  const [loading, setLoading] = useState(false)

  if (!isHost()) {
    nav('/host/login')
    return null
  }

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const game = await gamesApi.create(form)
      toast.success(`Room created: ${game.room_code}`)
      nav(`/host/dashboard/${game.room_code}`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to create game')
    } finally {
      setLoading(false)
    }
  }

  const Field = ({ label, name, type = 'text', min, max }: {
    label: string; name: keyof typeof form; type?: string; min?: number; max?: number
  }) => (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">{label}</label>
      <input className="input" type={type} min={min} max={max}
        value={form[name]} onChange={e => setForm(f => ({ ...f, [name]: type === 'number' ? Number(e.target.value) : e.target.value }))} />
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-900 px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-lg">
        <div className="text-center mb-8"><Logo size="md" /></div>
        <div className="card p-8">
          <h2 className="text-2xl font-bold mb-6">Create Contest Room</h2>
          <form onSubmit={create} className="space-y-4">
            <Field label="Contest Title" name="title" />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Max Players (2–70)" name="max_players" type="number" min={2} max={70} />
              <Field label="Total Rounds" name="total_rounds" type="number" min={1} max={20} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Round Duration (sec)" name="round_duration" type="number" min={30} max={3600} />
              <Field label="Max Attempts" name="max_attempts" type="number" min={1} max={10} />
            </div>
            <button type="submit" className="btn-primary w-full py-3 text-base mt-2" disabled={loading}>
              {loading ? 'Creating...' : '🚀 Create Room'}
            </button>
          </form>
          <p className="mt-4 text-center"><Link to="/" className="text-xs text-gray-500 hover:text-gray-400">← Back</Link></p>
        </div>
      </motion.div>
    </div>
  )
}
