import { create } from 'zustand'
import type {
  GameStatus, Player, Round, LeaderboardEntry,
  ScoreBreakdown, Submission, LobbyStatePayload,
} from '@/types/game'

interface GameState {
  // Room / lobby
  gameId: string | null
  roomCode: string | null
  gameTitle: string
  gameStatus: GameStatus
  maxPlayers: number
  totalRounds: number
  roundDuration: number
  maxAttempts: number
  players: Player[]

  // Current round
  currentRound: Round | null
  remainingSeconds: number

  // Submissions this round
  submissions: Submission[]
  currentSubmissionId: string | null
  isGenerating: boolean
  generatedImageUrl: string | null

  // Scores
  myScore: ScoreBreakdown | null
  leaderboard: LeaderboardEntry[]
  shortlistAdvanced: LeaderboardEntry[]
  shortlistEliminated: LeaderboardEntry[]

  // UI state
  isConnected: boolean
  countdownValue: number | null

  // Actions
  applyLobbyState: (payload: LobbyStatePayload) => void
  updatePlayer: (player: Partial<Player> & { id: string }) => void
  addPlayer: (player: Player) => void
  removePlayer: (playerId: string) => void
  setRound: (round: Round) => void
  setRemainingSeconds: (s: number) => void
  addSubmission: (sub: Submission) => void
  updateSubmission: (id: string, updates: Partial<Submission>) => void
  setCurrentSubmissionId: (id: string | null) => void
  setIsGenerating: (v: boolean) => void
  setGeneratedImageUrl: (url: string | null) => void
  setMyScore: (score: ScoreBreakdown) => void
  setLeaderboard: (entries: LeaderboardEntry[]) => void
  setShortlist: (advanced: LeaderboardEntry[], eliminated: LeaderboardEntry[]) => void
  setGameStatus: (status: GameStatus) => void
  setConnected: (v: boolean) => void
  setCountdown: (n: number | null) => void
  resetRound: () => void
}

export const useGameStore = create<GameState>((set) => ({
  gameId: null,
  roomCode: null,
  gameTitle: 'PromptX Prelims',
  gameStatus: 'LOBBY',
  maxPlayers: 70,
  totalRounds: 5,
  roundDuration: 60,
  maxAttempts: 3,
  players: [],
  currentRound: null,
  remainingSeconds: 0,
  submissions: [],
  currentSubmissionId: null,
  isGenerating: false,
  generatedImageUrl: null,
  myScore: null,
  leaderboard: [],
  shortlistAdvanced: [],
  shortlistEliminated: [],
  isConnected: false,
  countdownValue: null,

  applyLobbyState: (payload) => {
    set({
      gameId: payload.game_id,
      roomCode: payload.room_code,
      gameTitle: payload.title,
      gameStatus: payload.status,
      maxPlayers: payload.max_players,
      totalRounds: payload.total_rounds,
      roundDuration: payload.round_duration,
      maxAttempts: payload.max_attempts,
      players: payload.players,
    })
  },

  updatePlayer: (updates) => {
    set((state) => ({
      players: state.players.map((p) =>
        p.id === updates.id ? { ...p, ...updates } : p
      ),
    }))
  },

  addPlayer: (player) => {
    set((state) => {
      if (state.players.find((p) => p.id === player.id)) return state
      return { players: [...state.players, player] }
    })
  },

  removePlayer: (playerId) => {
    set((state) => ({
      players: state.players.filter((p) => p.id !== playerId),
    }))
  },

  setRound: (round) => set({ currentRound: round, submissions: [], myScore: null }),

  setRemainingSeconds: (s) => set({ remainingSeconds: s }),

  addSubmission: (sub) => {
    set((state) => ({
      submissions: [...state.submissions.filter((s) => s.id !== sub.id), sub],
    }))
  },

  updateSubmission: (id, updates) => {
    set((state) => ({
      submissions: state.submissions.map((s) => s.id === id ? { ...s, ...updates } : s),
    }))
  },

  setCurrentSubmissionId: (id) => set({ currentSubmissionId: id }),
  setIsGenerating: (v) => set({ isGenerating: v }),
  setGeneratedImageUrl: (url) => set({ generatedImageUrl: url }),
  setMyScore: (score) => set({ myScore: score }),
  setLeaderboard: (entries) => set({ leaderboard: entries }),

  setShortlist: (advanced, eliminated) =>
    set({ shortlistAdvanced: advanced, shortlistEliminated: eliminated }),

  setGameStatus: (status) => set({ gameStatus: status }),
  setConnected: (v) => set({ isConnected: v }),
  setCountdown: (n) => set({ countdownValue: n }),

  resetRound: () => set({
    submissions: [],
    currentSubmissionId: null,
    isGenerating: false,
    generatedImageUrl: null,
    myScore: null,
    remainingSeconds: 0,
  }),
}))
