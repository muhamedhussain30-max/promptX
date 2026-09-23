/**
 * API service — typed Axios wrappers for all REST endpoints.
 */
import axios from 'axios'
import type {
  GameSummary, LeaderboardEntry, ScoreBreakdown, Submission,
} from '@/types/game'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach auth headers — host token from localStorage, player token from sessionStorage (tab-isolated)
api.interceptors.request.use((config) => {
  const playerToken = sessionStorage.getItem('player_token')
  const hostToken = localStorage.getItem('host_token')

  // Player token takes priority — if this tab has a player session, never send the host token
  if (playerToken) {
    config.headers['X-Player-Token'] = playerToken
    delete config.headers['Authorization']
  } else if (hostToken) {
    config.headers['Authorization'] = `Bearer ${hostToken}`
    delete config.headers['X-Player-Token']
  }
  return config
})

// ── Response unwrapper ────────────────────────────────────────────────────────
type ApiResponse<T> = { success: boolean; data: T; message: string; error?: string }
function unwrap<T>(r: { data: ApiResponse<T> }): T {
  if (!r.data.success && r.data.error) throw new Error(r.data.error)
  return r.data.data
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (body: { username: string; email: string; password: string; display_name: string }) =>
    api.post('/auth/register', body).then(unwrap<{ id: string; username: string; display_name: string; is_host: boolean }>),

  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password })
       .then(unwrap<{ access_token: string; user_id: string; display_name: string; token_type: string }>),
}

// ── Games ─────────────────────────────────────────────────────────────────────

export const gamesApi = {
  create: (body: {
    title?: string; max_players?: number; total_rounds?: number;
    round_duration?: number; max_attempts?: number;
  }) => api.post('/games', body).then(unwrap<GameSummary>),

  get: (roomCode: string) =>
    api.get(`/games/${roomCode}`).then(unwrap<GameSummary>),

  join: (roomCode: string, display_name: string) =>
    api.post(`/games/${roomCode}/join`, { room_code: roomCode, display_name })
       .then(unwrap<{ player_id: string; session_token: string; game_id: string; room_code: string; display_name: string }>),

  start: (gameId: string) =>
    api.post(`/games/${gameId}/start`).then(unwrap<null>),

  getLeaderboard: (gameId: string) =>
    api.get(`/games/${gameId}/leaderboard`)
       .then(unwrap<{ game_id: string; round_number: number; entries: LeaderboardEntry[] }>),

  shortlist: (gameId: string, method: string, value: number) =>
    api.post(`/games/${gameId}/shortlist`, { method, value }).then(unwrap<null>),

  nextRound: (gameId: string) =>
    api.post(`/games/${gameId}/next-round`).then(unwrap<null>),

  end: (gameId: string) =>
    api.post(`/games/${gameId}/end`).then(unwrap<null>),
}

// ── Players ───────────────────────────────────────────────────────────────────

export const playersApi = {
  me: () => api.get('/players/me').then(unwrap),

  setReady: (isReady: boolean) =>
    api.post('/players/me/ready', { is_ready: isReady }).then(unwrap),

  getScores: (playerId: string) =>
    api.get(`/players/${playerId}/score`).then(unwrap<ScoreBreakdown[]>),

  getSubmissions: (playerId: string, roundId: string) =>
    api.get(`/players/${playerId}/submissions/${roundId}`).then(unwrap<Submission[]>),
}

// ── Rounds ────────────────────────────────────────────────────────────────────

export const roundsApi = {
  validatePrompt: (roundId: string, prompt: string) =>
    api.post(`/rounds/${roundId}/validate-prompt`, { prompt })
       .then(unwrap<{ is_valid: boolean; normalized_prompt: string; forbidden_words_detected: string[]; message: string }>),

  generateImage: (roundId: string, prompt: string) =>
    api.post(`/rounds/${roundId}/generate`, { prompt, attempt_number: 1 })
       .then(unwrap<{ submission_id: string; status: string; image_url: string | null; message: string }>),

  submit: (roundId: string, submissionId: string) =>
    api.post(`/rounds/${roundId}/submit`, { submission_id: submissionId }).then(unwrap<Submission>),
}

// ── Challenges ────────────────────────────────────────────────────────────────

export const challengesApi = {
  list: () => api.get('/challenges').then(unwrap),
  seed: () => api.post('/challenges/seed').then(unwrap),
}

export default api
