import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'react-hot-toast'
import { roundsApi } from '@/services/api'
import type { Submission } from '@/types/game'

interface ImageSubmissionProps {
  roundId: string
  submissions: Submission[]
  isGenerating: boolean
  disabled: boolean
}

export default function ImageSubmission({ roundId, submissions, isGenerating, disabled }: ImageSubmissionProps) {
  const [submitting, setSubmitting] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const completedSubs = submissions.filter(s => s.generation_completed && s.image_url)
  const finalSub = submissions.find(s => s.is_final)

  const submitFinal = async (submissionId: string) => {
    setSubmitting(true)
    try {
      await roundsApi.submit(roundId, submissionId)
      setSelectedId(submissionId)
      toast.success('Final submission recorded!', { icon: '✅' })
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  if (completedSubs.length === 0 && !isGenerating) return null

  return (
    <div className="card p-6 space-y-4">
      <h3 className="font-semibold text-gray-200">
        Generated Images
        {finalSub && <span className="ml-2 text-xs text-accent-green bg-accent-green/10 px-2 py-0.5 rounded-full">Submitted ✓</span>}
      </h3>

      {isGenerating && (
        <div className="flex items-center gap-3 py-4 text-gray-400">
          <div className="w-6 h-6 border-2 border-brand-500/40 border-t-brand-500 rounded-full animate-spin" />
          <span>Generating your image...</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <AnimatePresence>
          {completedSubs.map((sub) => {
            const isSelected = (selectedId ?? finalSub?.id) === sub.id
            return (
              <motion.div
                key={sub.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`relative rounded-xl overflow-hidden cursor-pointer border-2 transition-all ${
                  isSelected ? 'border-accent-green shadow-glow-green' : 'border-surface-600 hover:border-brand-500/50'
                }`}
                onClick={() => !disabled && !submitting && submitFinal(sub.id)}
              >
                <img
                  src={sub.image_url!}
                  alt={`Attempt ${sub.attempt_number}`}
                  className="w-full aspect-square object-cover"
                />
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-300">Attempt {sub.attempt_number}</span>
                    {isSelected
                      ? <span className="text-xs text-accent-green font-bold">✓ SELECTED</span>
                      : <span className="text-xs text-gray-400">Click to select</span>
                    }
                  </div>
                </div>
                {isSelected && (
                  <div className="absolute top-2 right-2 w-7 h-7 bg-accent-green rounded-full flex items-center justify-center">
                    <span className="text-sm font-bold text-white">✓</span>
                  </div>
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>

      {completedSubs.length > 0 && !finalSub && !disabled && (
        <p className="text-xs text-gray-500 text-center">Click an image to set it as your final submission</p>
      )}
    </div>
  )
}
