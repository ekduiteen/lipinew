/**
 * WebSocket client for the LIPI conversation stream.
 *
 * Binary frames  → audio (WAV bytes)
 * JSON text frames → metadata: token | tts_start | tts_end | empty_audio
 *
 * Usage:
 *   const ws = new LipiWebSocket(sessionId, userId, handlers);
 *   ws.sendAudio(pcmBytes);
 *   ws.close();
 */

export interface WSHandlers {
  onOpen?: () => void;
  onTranscript: (text: string, language?: string, confidence?: number) => void;
  onToken: (text: string) => void;
  onTTSStart: (text: string, turn: number) => void;
  onAudio: (wav: ArrayBuffer) => void;
  onTTSEnd: () => void;
  onEmptyAudio: () => void;
  onError: (err: Event) => void;
  onClose: () => void;
}

function resolveWsBase(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit) return explicit;

  if (typeof window === "undefined") return "";

  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.hostname;
  const port = window.location.port === "3000" ? "8000" : window.location.port;

  return `${scheme}://${host}${port ? `:${port}` : ""}`;
}

// WebSocket connects directly to backend (not proxied)
const WS_BASE = resolveWsBase();

export class LipiWebSocket {
  private ws: WebSocket | null = null;
  private _expectingAudio = false;

  constructor(sessionId: string, userId: string, private handlers: WSHandlers) {
    // Fetch short-lived WebSocket token, then create the real connection.
    this._initializeConnection(sessionId, userId);
  }

  private async _initializeConnection(sessionId: string, userId: string): Promise<void> {
    try {
      // Get short-lived WebSocket token from backend via frontend endpoint
      // This endpoint reads the httpOnly cookie and gets a 5-min token
      const tokenRes = await fetch("/api/auth/ws-token", { method: "POST" });
      if (!tokenRes.ok) {
        throw new Error(`Failed to get WebSocket token: ${tokenRes.status}`);
      }
      const { ws_token } = (await tokenRes.json()) as { ws_token: string };

      const url = `${WS_BASE}/ws/session/${sessionId}?token=${encodeURIComponent(ws_token)}`;
      this.ws = new WebSocket(url);
      this.ws.binaryType = "arraybuffer";
      this.ws.onopen = () => this.handlers.onOpen?.();
      this.ws.onmessage = this._onMessage.bind(this);
      this.ws.onerror = this.handlers.onError;
      this.ws.onclose = this.handlers.onClose;
    } catch (err: any) {
      this.handlers.onError(new Event("error"));
      console.error("Failed to initialize WebSocket:", err);
    }
  }

  get readyState() {
    return this.ws?.readyState ?? WebSocket.CONNECTING;
  }

  sendAudio(bytes: ArrayBuffer | Uint8Array): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(bytes);
    }
  }

  close(): void {
    this.ws?.close();
  }

  private _onMessage(ev: MessageEvent): void {
    if (ev.data instanceof ArrayBuffer) {
      this.handlers.onAudio(ev.data);
      return;
    }

    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(ev.data as string) as Record<string, unknown>;
    } catch {
      return;
    }

    switch (msg.type) {
      case "token":
        this.handlers.onToken(msg.text as string);
        break;
      case "transcript":
        this.handlers.onTranscript(
          msg.text as string,
          msg.language as string | undefined,
          msg.confidence as number | undefined,
        );
        break;
      case "tts_start":
        this._expectingAudio = true;
        this.handlers.onTTSStart(msg.text as string, msg.turn as number);
        break;
      case "tts_end":
        this._expectingAudio = false;
        this.handlers.onTTSEnd();
        break;
      case "empty_audio":
        this.handlers.onEmptyAudio();
        break;
    }
  }
}
