import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  // Host
  hostToken: string | null
  hostId: string | null
  hostDisplayName: string | null
  // Player — stored per-player-id so multiple tabs don't overwrite each other
  playerToken: string | null
  playerId: string | null
  playerDisplayName: string | null
  gameId: string | null
  roomCode: string | null

  setHost: (token: string, id: string, displayName: string) => void
  setPlayer: (token: string, id: string, displayName: string, gameId: string, roomCode: string) => void
  clearHost: () => void
  clearPlayer: () => void
  isHost: () => boolean
  isPlayer: () => boolean
}

// Each browser tab gets its own sessionStorage key — tabs never share player sessions
// We use sessionStorage (not localStorage) for player tokens so:
//   - Closing the tab clears the session
//   - Two tabs in the same browser each have their own independent player token
const SESSION_KEY = 'promptx-player-session'

function savePlayerSession(data: {
  playerToken: string; playerId: string; playerDisplayName: string;
  gameId: string; roomCode: string;
}) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(data))
  // Also expose for the Axios interceptor to read
  sessionStorage.setItem('player_token', data.playerToken)
}

function clearPlayerSession() {
  sessionStorage.removeItem(SESSION_KEY)
  sessionStorage.removeItem('player_token')
}

function loadPlayerSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => {
      // Restore player session from sessionStorage on init
      const saved = loadPlayerSession()

      return {
        hostToken: null,
        hostId: null,
        hostDisplayName: null,
        playerToken: saved?.playerToken ?? null,
        playerId: saved?.playerId ?? null,
        playerDisplayName: saved?.playerDisplayName ?? null,
        gameId: saved?.gameId ?? null,
        roomCode: saved?.roomCode ?? null,

        setHost: (token, id, displayName) => {
          // Host uses localStorage (intentionally persists across tabs)
          localStorage.setItem('host_token', token)
          // Make sure no stale player token leaks into host tab
          sessionStorage.removeItem('player_token')
          set({ hostToken: token, hostId: id, hostDisplayName: displayName })
        },

        setPlayer: (token, id, displayName, gameId, roomCode) => {
          // Player uses sessionStorage — tab-isolated
          savePlayerSession({ playerToken: token, playerId: id, playerDisplayName: displayName, gameId, roomCode })
          // Clear any host token from this tab so it doesn't interfere
          set({
            playerToken: token,
            playerId: id,
            playerDisplayName: displayName,
            gameId,
            roomCode,
            // Clear host from player tabs
            hostToken: null,
            hostId: null,
            hostDisplayName: null,
          })
        },

        clearHost: () => {
          localStorage.removeItem('host_token')
          set({ hostToken: null, hostId: null, hostDisplayName: null })
        },

        clearPlayer: () => {
          clearPlayerSession()
          set({ playerToken: null, playerId: null, playerDisplayName: null, gameId: null, roomCode: null })
        },

        isHost: () => Boolean(get().hostToken),
        isPlayer: () => Boolean(get().playerToken),
      }
    },
    {
      name: 'promptx-auth',
      // Only persist host data in localStorage — player data uses sessionStorage
      partialize: (s) => ({
        hostToken: s.hostToken,
        hostId: s.hostId,
        hostDisplayName: s.hostDisplayName,
        // DO NOT persist player tokens in localStorage — they use sessionStorage
      }),
    },
  ),
)
