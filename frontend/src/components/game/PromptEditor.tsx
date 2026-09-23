import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'react-hot-toast'
import { roundsApi } from '@/services/api'
import { useGameStore } from '@/stores/gameStore'
import wsService from '@/services/websocket'

interface Props {
  roundId: string
  forbiddenWords: string[]
  maxAttempts: number
  attemptsUsed: number
  onGenerate: (submissionId: string, prompt: string) => void
  disabled?: boolean
}

function detectForbidden(text: string, words: string[]): string[] {
  const lo = text.toLowerCase()
  return words.filter(w => {
    const esc = w.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    return new RegExp(`\\b${esc}s?\\b`).test(lo)
  })
}

/** Wrap forbidden words in text with a <mark> span for highlighting. */
function highlightForbidden(text: string, words: string[]): string {
  if (!words.length || !text) return escapeHtml(text)
  let result = escapeHtml(text)
  for (const w of words) {
    const esc = w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    result = result.replace(
      new RegExp(`(\\b${esc}s?\\b)`, 'gi'),
      '<mark class="forbidden-highlight">$1</mark>',
    )
  }
  return result
}

function escapeHtml(s: string) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}

export default function PromptEditor({
  roundId, forbiddenWords, maxAttempts, attemptsUsed, onGenerate, disabled = false,
}: Props) {
  const [prompt, setPrompt]     = useState('')
  const [validating, setVal]    = useState(false)
  const [submitting, setSub]    = useState(false)
  const [submitted, setDone]    = useState(false)
  const [shake, setShake]       = useState(false)
  const [serverOk, setServerOk] = useState<boolean | null>(null)
  const [serverMsg, setServerMsg] = useState('')

  const pendingId   = useRef<string | null>(null)
  const pendingRid  = useRef(roundId)
  const taRef       = useRef<HTMLTextAreaElement>(null)
  const overlayRef  = useRef<HTMLDivElement>(null)

  const isGenerating = useGameStore(s => s.isGenerating)
  const detected     = detectForbidden(prompt, forbiddenWords)
  const hasForbidden = detected.length > 0
  const wordCount    = prompt.trim().split(/\s+/).filter(Boolean).length
  const charCount    = prompt.length
  const attemptsLeft = maxAttempts - attemptsUsed
  const canSubmit    = !hasForbidden && !submitting && !submitted && !isGenerating
                       && !disabled && prompt.trim().length > 3

  useEffect(() => { pendingRid.current = roundId }, [roundId])

  // Sync overlay scroll with textarea
  const syncScroll = useCallback(() => {
    if (overlayRef.current && taRef.current) {
      overlayRef.current.scrollTop = taRef.current.scrollTop
    }
  }, [])

  // Debounced server validation
  useEffect(() => {
    if (!prompt.trim()) { setServerOk(null); setServerMsg(''); return }
    const t = setTimeout(async () => {
      try {
        setVal(true)
        const r = await roundsApi.validatePrompt(roundId, prompt)
        setServerOk(r.is_valid)
        setServerMsg(r.message)
      } catch { /* ignore */ } finally { setVal(false) }
    }, 650)
    return () => clearTimeout(t)
  }, [prompt, roundId])

  // Auto-submit once image arrives
  useEffect(() => {
    const unsub = wsService.on('image_generated', async (data) => {
      const d = data as { submission_id: string; image_url: string }
      if (pendingId.current !== d.submission_id) return
      try {
        await roundsApi.submit(pendingRid.current, d.submission_id)
        setDone(true)
        pendingId.current = null
        toast.success('Submitted! Waiting for results…', { icon: '✅', duration: 4000 })
      } catch (e: unknown) {
        const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Auto-submit failed'
        toast.error(msg)
        setSub(false)
      }
    })
    return unsub
  }, [])

  const triggerShake = () => {
    setShake(true)
    setTimeout(() => setShake(false), 450)
  }

  const handleSubmit = async () => {
    if (!canSubmit) { if (hasForbidden) triggerShake(); return }
    setSub(true)
    try {
      const res = await roundsApi.generateImage(roundId, prompt)
      if (!res.submission_id || res.status === 'rejected') {
        toast.error(res.message || 'Prompt rejected')
        setSub(false)
        triggerShake()
        return
      }
      pendingId.current = res.submission_id
      onGenerate(res.submission_id, prompt)
      toast('Generating — will auto-submit when ready', { icon: '🎨' })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string; message?: string } }; message?: string })
        ?.response?.data?.detail ?? 'Submission failed'
      toast.error(msg)
      setSub(false)
      triggerShake()
    }
  }

  // Button label
  let btnLabel: React.ReactNode = (
    <><span className="mr-1">📝</span> SUBMIT PROMPT</>
  )
  if (submitted) btnLabel = <><span className="mr-1">✅</span> SUBMITTED</>
  else if (isGenerating || (submitting && !submitted))
    btnLabel = (
      <span className="flex items-center gap-2">
        <span className="w-4 h-4 border-2 border-current/30 border-t-current rounded-full animate-spin" />
        {isGenerating ? 'Generating…' : 'Submitting…'}
      </span>
    )
  else if (hasForbidden) btnLabel = <><span className="mr-1">⛔</span> REMOVE FORBIDDEN WORDS</>
  else if (attemptsLeft <= 0) btnLabel = <><span className="mr-1">🚫</span> ALREADY SUBMITTED</>

  const btnClass = submitted
    ? 'btn w-full py-4 text-base border border-neon-green/40 bg-neon-green/10 text-neon-green cursor-not-allowed'
    : !canSubmit
    ? 'btn w-full py-4 text-base bg-surface-700 text-white/25 border border-white/8 cursor-not-allowed'
    : 'btn-cyan w-full py-4 text-base font-display tracking-wider'

  return (
    <div className="card p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-heading font-semibold text-white/80 text-sm uppercase tracking-widest">
          Your Prompt
        </h3>
        <div className="flex gap-3 text-xs font-mono">
          <span className="text-white/40">
            <span className="text-white/70">{wordCount}</span> words
          </span>
          <span className="text-white/40">
            <span className="text-white/70">{charCount}</span>/2000
          </span>
          {!submitted && (
            <span className={attemptsLeft <= 0 ? 'text-neon-red font-bold' : 'text-neon-yellow/80'}>
              {attemptsLeft > 0 ? `${attemptsLeft} attempt${attemptsLeft !== 1 ? 's' : ''}` : 'submitted'}
            </span>
          )}
        </div>
      </div>

      {/* Textarea with inline forbidden-word highlight overlay */}
      <motion.div
        animate={shake ? { x: [-6, 6, -4, 4, 0] } : {}}
        transition={{ duration: 0.38 }}
        className="relative"
      >
        {/* Highlight overlay (pointer-events:none, exact same sizing) */}
        <div
          ref={overlayRef}
          aria-hidden
          className="absolute inset-0 rounded-xl px-4 py-3 text-base leading-relaxed font-sans
                     overflow-hidden pointer-events-none whitespace-pre-wrap break-words"
          style={{
            color: 'transparent',
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: '1rem',
            lineHeight: '1.625',
            zIndex: 1,
          }}
          dangerouslySetInnerHTML={{ __html: highlightForbidden(prompt, forbiddenWords) }}
        />
        <textarea
          ref={taRef}
          className={`input resize-none h-36 text-base leading-relaxed relative z-10 bg-transparent
            ${hasForbidden ? 'input-error' : ''}
            ${submitted || disabled || isGenerating ? 'opacity-60' : ''}
          `}
          style={{
            caretColor: '#00E5FF',
            color: hasForbidden ? 'rgba(255,255,255,0.85)' : '#E0E0F0',
            background: 'rgba(11,11,20,0.85)',
          }}
          placeholder="Describe the target image without using the forbidden words…"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onScroll={syncScroll}
          disabled={disabled || isGenerating || submitting || submitted}
          maxLength={2000}
          spellCheck={false}
        />
        {validating && (
          <span className="absolute bottom-2.5 right-3 text-xs text-cyan-DEFAULT/50 animate-pulse font-mono z-20">
            checking…
          </span>
        )}
      </motion.div>

      {/* Forbidden word list */}
      <AnimatePresence>
        {hasForbidden && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="card-red px-4 py-3 space-y-2"
          >
            <p className="text-xs font-heading font-bold text-neon-red uppercase tracking-widest">
              ⚠ Forbidden words detected — remove before submitting:
            </p>
            <div className="flex flex-wrap gap-2">
              {detected.map(w => (
                <span key={w} className="forbidden-chip animate-shake">{w}</span>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Server validation feedback */}
      <AnimatePresence>
        {serverOk !== null && !hasForbidden && (
          <motion.div
            initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className={`flex items-center gap-2 text-sm px-3 py-2 rounded-xl ${
              serverOk
                ? 'bg-neon-green/8 border border-neon-green/25 text-neon-green'
                : 'bg-neon-red/10 border border-neon-red/30 text-neon-red'
            }`}
          >
            {serverOk ? '✓' : '✗'} {serverMsg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit button */}
      <motion.button
        whileTap={canSubmit ? { scale: 0.97 } : {}}
        onClick={handleSubmit}
        disabled={!canSubmit && !hasForbidden}
        className={btnClass}
        style={{ letterSpacing: submitted ? undefined : '0.08em' }}
        aria-label="Submit your prompt"
      >
        {btnLabel}
      </motion.button>

      {/* Status hint */}
      {!submitted && !hasForbidden && serverOk && (
        <p className="text-xs text-white/25 text-center">
          Image will be generated and submitted automatically.
        </p>
      )}
      {submitted && (
        <p className="text-xs text-neon-green/60 text-center">
          ✓ Your image is submitted — waiting for the round to end.
        </p>
      )}
    </div>
  )
}
