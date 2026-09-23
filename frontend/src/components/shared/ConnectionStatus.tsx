import { useGameStore } from '@/stores/gameStore'

export default function ConnectionStatus() {
  const connected = useGameStore(s => s.isConnected)
  return (
    <div className={`flex items-center gap-1.5 text-xs font-heading font-semibold ${
      connected ? 'text-neon-green' : 'text-neon-red'
    }`}>
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
        connected ? 'bg-neon-green animate-pulse' : 'bg-neon-red'
      }`} style={connected ? { boxShadow: '0 0 6px rgba(57,255,154,0.8)' } : {}} />
      <span className="hidden sm:inline">{connected ? 'LIVE' : 'OFFLINE'}</span>
    </div>
  )
}
