import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import Logo from '@/components/shared/Logo'
import { authApi } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

export default function HostLoginPage() {
  const nav = useNavigate()
  const setHost = useAuthStore((s) => s.setHost)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [form, setForm] = useState({ username: '', password: '', email: '', display_name: '' })
  const [loading, setLoading] = useState(false)

  const handle = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'register') {
        await authApi.register(form)
        toast.success('Account created! Please log in.')
        setMode('login')
      } else {
        const res = await authApi.login(form.username, form.password)
        setHost(res.access_token, res.user_id, res.display_name)
        toast.success(`Welcome, ${res.display_name}!`)
        nav('/host/create')
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-900 px-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="text-center mb-8"><Logo size="md" /></div>
        <div className="card p-8">
          <h2 className="text-2xl font-bold mb-6 text-center">
            {mode === 'login' ? 'Host Login' : 'Create Host Account'}
          </h2>
          <form onSubmit={handle} className="space-y-4">
            <input className="input" placeholder="Username" value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))} required />
            {mode === 'register' && <>
              <input className="input" placeholder="Email" type="email" value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
              <input className="input" placeholder="Display Name" value={form.display_name}
                onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} required />
            </>}
            <input className="input" placeholder="Password" type="password" value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
            <button type="submit" className="btn-primary w-full py-3 text-base" disabled={loading}>
              {loading ? 'Loading...' : mode === 'login' ? 'Login' : 'Register'}
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-gray-400">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              className="text-brand-400 hover:text-brand-300 font-medium">
              {mode === 'login' ? 'Register' : 'Login'}
            </button>
          </p>
          <p className="mt-2 text-center"><Link to="/" className="text-xs text-gray-500 hover:text-gray-400">← Back</Link></p>
        </div>
      </motion.div>
    </div>
  )
}
