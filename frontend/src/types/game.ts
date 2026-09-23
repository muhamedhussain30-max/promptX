// ── Enums (must match backend Python enums exactly) ───────────────────────────

export type GameStatus =
  | 'LOBBY'
  | 'COUNTDOWN'
  | 'ROUND_ACTIVE'
  | 'ROUND_PROCESSING'
  | 'LEADERBOARD'
  | 'SHORTLISTING'
  | 'NEXT_ROUND'
  | 'FINISHED'

export type PlayerStatus =
  | 'WAITING'
  | 'READY'
  | 'ACTIVE'
  | 'SUBMITTED'
  | 'ELIMINATED'
  | 'ADVANCED'
  | 'WINNER'
  | 'DISCONNECTED'

export type Difficulty = 'EASY' | 'MEDIUM' | 'HARD' | 'EXPERT'
export type ChallengeCategory =
  | 'Animals' | 'People' | 'Food' | 'Vehicles' | 'Fantasy'
  | 'Architecture' | 'Nature' | 'Sports' | 'Movies' | 'Objects'
  | 'Surreal' | 'Technology'

// ── Domain objects ────────────────────────────────────────────────────────────

export interface Player {
  id: string
  display_name: string
  status: PlayerStatus
  is_ready: boolean
  total_score: number
  rank: number | null
}

export interface Challenge {
  id: string
  target_description: string
  forbidden_words: string[]
  difficulty: Difficulty
  category: ChallengeCategory
}

export interface Round {
  round_id: string
  round_number: number
  total_rounds: number
  ends_at: string         // ISO timestamp (authoritative server time)
  duration: number        // seconds
  challenge: Challenge
}

export interface GameSummary {
  id: string
  title: string
  room_code: string
  status: GameStatus
  player_count: number
  max_players: number
  current_round_number: number
  total_rounds: number
}

export interface ConceptResult {
  label: string           // "Subject" | "Detail" | "Environment" | "Action"
  result: 'yes' | 'partial' | 'no'
}

export interface ScoreBreakdown {
  // ── Anti-gaming final score ─────────────────────────────────────
  total: number           // 0-100 final ranking score

  // ── 0-100 components (new) ──────────────────────────────────────
  match_score:       number   // image match 0-100
  creativity_100:    number   // 0-100
  speed_100:         number   // 0-100
  efficiency_100:    number   // 0-100
  subject_score:     number   // 0-100
  scene_score:       number   // 0-100
  composition_score: number   // 0-100
  concept_coverage:  number   // 0-100

  // ── Legacy 0-10 / 0-50 columns (kept for leaderboard compat) ──
  accuracy:    number   // match_score//2 (0-50)
  compliance:  number   // 20
  creativity:  number   // 0-10
  speed:       number   // 0-10
  efficiency:  number   // 0-10

  // ── Rubric detail ───────────────────────────────────────────────
  accuracy_breakdown?: {
    concepts?: ConceptResult[]
    match_score?: number
    subject_score?: number
    scene_score?: number
    composition_score?: number
    concept_coverage?: number
    [key: string]: unknown
  }
  image_url?:   string | null
  raw_prompt?:  string | null
}

export interface AccuracyBreakdown {
  object_accuracy: number
  attribute_accuracy: number
  scene_accuracy: number
  relationship_accuracy: number
  total: number
  objects: { name: string; present: boolean; awarded: number; max: number }[]
}

export interface LeaderboardEntry {
  rank: number
  player_id: string
  display_name: string
  round_score: number
  cumulative_score: number
  is_advanced: boolean | null
  accuracy: number
  speed: number
}

export interface Submission {
  id: string
  round_id: string
  player_id: string
  attempt_number: number
  raw_prompt: string
  is_valid: boolean
  image_url: string | null
  is_final: boolean
  generation_completed: boolean
}

// ── WebSocket event payloads ──────────────────────────────────────────────────

export type ServerEventType =
  | 'connected' | 'error'
  | 'player_joined' | 'player_left' | 'player_ready' | 'player_unready' | 'lobby_state'
  | 'game_started' | 'countdown_started' | 'countdown_tick'
  | 'round_started' | 'timer_updated' | 'round_ended' | 'round_processing'
  | 'prompt_validated' | 'image_generation_started' | 'image_generated' | 'submission_completed'
  | 'score_calculated' | 'leaderboard_updated'
  | 'player_advanced' | 'player_eliminated' | 'shortlist_announced'
  | 'next_round_started' | 'game_finished' | 'winner_announced'
  | 'game_paused' | 'game_resumed' | 'player_removed'
  | 'pong'

export interface WSMessage<T = unknown> {
  event: ServerEventType
  data: T
}

export interface LobbyStatePayload {
  game_id: string
  title: string
  room_code: string
  status: GameStatus
  max_players: number
  total_rounds: number
  round_duration: number
  max_attempts: number
  players: Player[]
  player_count: number
}
