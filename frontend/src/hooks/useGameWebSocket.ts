/**
 * useGameWebSocket — connects the WebSocket service to the Zustand game store.
 * Mount this once at the room/game level; it registers all event handlers.
 */
import { useEffect } from 'react'
import { toast } from 'react-hot-toast'
import wsService from '@/services/websocket'
import { useGameStore } from '@/stores/gameStore'
import type {
  LobbyStatePayload, Player, Round, LeaderboardEntry,
  ScoreBreakdown, Submission,
} from '@/types/game'

interface UseGameWSOptions {
  roomCode: string
  token: string
  isHost?: boolean
}

export function useGameWebSocket({ roomCode, token, isHost = false }: UseGameWSOptions) {
  const store = useGameStore()

  useEffect(() => {
    wsService.connect(roomCode, token, isHost)

    const unsubs = [
      wsService.on('connected', () => store.setConnected(true)),

      wsService.on('error', (data) => {
        const d = data as { message: string }
        toast.error(d.message)
      }),

      wsService.on('lobby_state', (data) => {
        store.applyLobbyState(data as LobbyStatePayload)
      }),

      wsService.on('player_joined', (data) => {
        const d = data as { player: Player }
        // lobby_state broadcast handles the list update; this is just for the toast
        store.addPlayer(d.player)
        if (d.player.display_name) {
          toast(`${d.player.display_name} joined`, { icon: '👋' })
        }
      }),

      wsService.on('player_left', (data) => {
        const d = data as { player_id: string; display_name: string }
        store.removePlayer(d.player_id)
      }),

      wsService.on('player_ready', (data) => {
        const d = data as { player_id: string; is_ready: boolean }
        store.updatePlayer({ id: d.player_id, is_ready: d.is_ready })
      }),

      wsService.on('player_unready', (data) => {
        const d = data as { player_id: string }
        store.updatePlayer({ id: d.player_id, is_ready: false })
      }),

      wsService.on('game_started', () => {
        store.setGameStatus('COUNTDOWN')
        toast.success('Game is starting!', { icon: '🎮' })
      }),

      wsService.on('countdown_tick', (data) => {
        const d = data as { remaining: number }
        store.setCountdown(d.remaining)
        store.setGameStatus('COUNTDOWN')
      }),

      wsService.on('round_started', (data) => {
        const round = data as Round
        store.setRound(round)
        store.setGameStatus('ROUND_ACTIVE')
        store.setCountdown(null)
        // Seed timer immediately from server's ends_at so it never shows 0
        if (round.ends_at) {
          const remaining = Math.max(0, (new Date(round.ends_at).getTime() - Date.now()) / 1000)
          store.setRemainingSeconds(remaining)
        }
        toast(`Round ${round.round_number} started!`, { icon: '🎯' })
      }),

      wsService.on('timer_updated', (data) => {
        const d = data as { remaining_seconds: number }
        store.setRemainingSeconds(d.remaining_seconds)
      }),

      wsService.on('round_ended', () => {
        store.setGameStatus('ROUND_PROCESSING')
        toast('Round over! Calculating scores...', { icon: '⏰' })
      }),

      wsService.on('round_processing', () => {
        store.setGameStatus('ROUND_PROCESSING')
      }),

      wsService.on('image_generation_started', (data) => {
        const d = data as { submission_id: string }
        store.setIsGenerating(true)
        store.setCurrentSubmissionId(d.submission_id)
      }),

      wsService.on('image_generated', (data) => {
        const d = data as { submission_id: string; image_url: string; attempt_number: number }
        store.setIsGenerating(false)
        store.setGeneratedImageUrl(d.image_url)
        // Single canonical update — addSubmission checks for existing id and replaces it
        store.addSubmission({
          id: d.submission_id,
          round_id: store.currentRound?.round_id ?? '',
          player_id: store.currentRound?.round_id ?? '',   // placeholder — not used in UI
          attempt_number: d.attempt_number,
          raw_prompt: '',
          is_valid: true,
          image_url: d.image_url,
          is_final: false,
          generation_completed: true,
        } as Submission)
        toast.success('Image generated!', { icon: '🖼️' })
      }),

      wsService.on('submission_completed', () => {
        toast.success('Submission received!', { icon: '✅' })
      }),

      wsService.on('score_calculated', (data) => {
        const d = data as ScoreBreakdown & {
          match_score?: number; subject_score?: number; scene_score?: number;
          composition_score?: number; concept_coverage?: number;
          creativity_100?: number; speed_100?: number; efficiency_100?: number;
          image_url?: string; raw_prompt?: string;
        }
        // Normalise: fill in 0-100 fields if backend sent them flat
        const score: ScoreBreakdown = {
          total:             d.total ?? 0,
          match_score:       d.match_score ?? (d.accuracy ?? 0) * 2,
          creativity_100:    d.creativity_100 ?? (d.creativity ?? 0) * 10,
          speed_100:         d.speed_100 ?? (d.speed ?? 0) * 10,
          efficiency_100:    d.efficiency_100 ?? (d.efficiency ?? 0) * 10,
          subject_score:     d.subject_score ?? 0,
          scene_score:       d.scene_score ?? 0,
          composition_score: d.composition_score ?? 0,
          concept_coverage:  d.concept_coverage ?? 0,
          accuracy:          d.accuracy ?? 0,
          compliance:        d.compliance ?? 20,
          creativity:        d.creativity ?? 0,
          speed:             d.speed ?? 0,
          efficiency:        d.efficiency ?? 0,
          accuracy_breakdown: d.accuracy_breakdown,
          image_url:         d.image_url ?? null,
          raw_prompt:        d.raw_prompt ?? null,
        }
        store.setMyScore(score)
        toast.success('Your score is ready!', { icon: '🏆' })
      }),

      wsService.on('leaderboard_updated', (data) => {
        const d = data as { entries: LeaderboardEntry[] }
        store.setLeaderboard(d.entries)
        store.setGameStatus('LEADERBOARD')
      }),

      wsService.on('shortlist_announced', (data) => {
        const d = data as { advanced: LeaderboardEntry[]; eliminated: LeaderboardEntry[] }
        store.setShortlist(d.advanced, d.eliminated)
        // Merge all into leaderboard with advancement status
        const all = [
          ...d.advanced.map(e => ({ ...e, is_advanced: true as const })),
          ...d.eliminated.map(e => ({ ...e, is_advanced: false as const })),
        ].sort((a, b) => a.rank - b.rank)
        store.setLeaderboard(all)
        store.setGameStatus('SHORTLISTING')
      }),

      wsService.on('player_advanced', (data) => {
        const d = data as { player_id: string }
        store.updatePlayer({ id: d.player_id, status: 'ADVANCED' })
      }),

      wsService.on('player_eliminated', (data) => {
        const d = data as { player_id: string }
        store.updatePlayer({ id: d.player_id, status: 'ELIMINATED' })
      }),

      wsService.on('next_round_started', (data) => {
        const d = data as { next_round_number: number }
        store.setGameStatus('NEXT_ROUND')
        store.resetRound()
        toast(`Preparing Round ${d.next_round_number}...`, { icon: '▶️' })
      }),

      wsService.on('game_finished', () => {
        store.setGameStatus('FINISHED')
        toast('Contest complete!', { icon: '🎊', duration: 6000 })
      }),

      wsService.on('winner_announced', (data) => {
        const d = data as { winners: LeaderboardEntry[] }
        store.setLeaderboard(d.winners)
      }),

      wsService.on('player_removed', () => {
        toast.error('You have been removed from the game by the host.')
        wsService.disconnect()
      }),
    ]

    return () => {
      // Just unsubscribe event handlers — keep WS alive for page navigation
      // The connection manager will reconnect if needed on next mount
      unsubs.forEach((fn) => fn())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomCode, token, isHost])
}
