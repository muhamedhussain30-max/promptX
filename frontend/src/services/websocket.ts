/**
 * WebSocketService — manages the single persistent WebSocket connection.
 *
 * Design:
 *  - Singleton instance accessed via getWS()
 *  - Auto-reconnect with exponential backoff (max 30s)
 *  - Typed event subscription system
 *  - Heartbeat ping every 20s to detect dead connections
 */
import type { ServerEventType, WSMessage } from '@/types/game'

type EventHandler = (data: unknown) => void

const WS_BASE = (import.meta as any).env?.VITE_WS_URL ?? 'ws://localhost:8001'
const MAX_RECONNECT_DELAY = 30_000
const PING_INTERVAL = 20_000

class WebSocketService {
  private ws: WebSocket | null = null
  private handlers: Map<ServerEventType, Set<EventHandler>> = new Map()
  private reconnectDelay = 1_000
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private shouldReconnect = false
  private connectParams: { roomCode: string; token: string; isHost: boolean } | null = null

  // ── Connect / disconnect ─────────────────────────────────────────────────

  connect(roomCode: string, token: string, isHost = false): void {
    // If already connected to this exact room+token, do nothing
    if (
      this.connectParams?.roomCode === roomCode &&
      this.connectParams?.token === token &&
      this.ws?.readyState === WebSocket.OPEN
    ) return

    // Disconnect any existing connection first
    if (this.ws) {
      this.shouldReconnect = false
      this._clearPing()
      this.ws.close(1000, 'Reconnecting')
      this.ws = null
    }

    this.connectParams = { roomCode, token, isHost }
    this.shouldReconnect = true
    this._open()
  }

  disconnect(): void {
    this.shouldReconnect = false
    this._clearPing()
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  private _open(): void {
    if (!this.connectParams) return
    const { roomCode, token, isHost } = this.connectParams
    const url = `${WS_BASE}/ws/${roomCode}?token=${encodeURIComponent(token)}&is_host=${isHost ? 1 : 0}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.debug('[WS] Connected', roomCode)
      this.reconnectDelay = 1_000
      this._startPing()
      this._emit('connected', {})
    }

    this.ws.onmessage = (ev: MessageEvent) => {
      try {
        const msg: WSMessage = JSON.parse(ev.data as string)
        this._emit(msg.event, msg.data)
      } catch {
        console.warn('[WS] Unparseable message', ev.data)
      }
    }

    this.ws.onerror = (ev) => {
      console.warn('[WS] Error', ev)
    }

    this.ws.onclose = (ev) => {
      this._clearPing()
      console.debug('[WS] Closed', ev.code, ev.reason)
      if (this.shouldReconnect && ev.code !== 1000) {
        setTimeout(() => this._open(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY)
      }
    }
  }

  // ── Send ─────────────────────────────────────────────────────────────────

  send(event: string, data: Record<string, unknown> = {}): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ event, data }))
    } else {
      console.warn('[WS] Not connected — cannot send', event)
    }
  }

  // ── Subscriptions ────────────────────────────────────────────────────────

  on(event: ServerEventType, handler: EventHandler): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set())
    this.handlers.get(event)!.add(handler)
    return () => this.off(event, handler)
  }

  off(event: ServerEventType, handler: EventHandler): void {
    this.handlers.get(event)?.delete(handler)
  }

  private _emit(event: ServerEventType, data: unknown): void {
    this.handlers.get(event)?.forEach((h) => h(data))
  }

  // ── Ping ─────────────────────────────────────────────────────────────────

  private _startPing(): void {
    this._clearPing()
    this.pingTimer = setInterval(() => this.send('ping', {}), PING_INTERVAL)
  }

  private _clearPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Singleton
const wsService = new WebSocketService()
export default wsService
