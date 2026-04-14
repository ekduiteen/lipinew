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
  onToken: (text: string) => void;
  onTTSStart: (text: string, turn: number) => void;
  onAudio: (wav: ArrayBuffer) => void;
  onTTSEnd: () => void;
  onEmptyAudio: () => void;
  onError: (err: Event) => void;
  onClose: () => void;
}

// WebSocket connects directly to backend (not proxied)
const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ??
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
    : "");

export class LipiWebSocket {
  private ws: WebSocket;
  private _expectingAudio = false;

  constructor(sessionId: string, userId: string, private handlers: WSHandlers) {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("lipi.token") : "";
    const url = `${WS_BASE}/ws/session/${sessionId}?user_id=${userId}&token=${token ?? ""}`;
    this.ws = new WebSocket(url);
    this.ws.binaryType = "arraybuffer";
    this.ws.onmessage = this._onMessage.bind(this);
    this.ws.onerror = handlers.onError;
    this.ws.onclose = handlers.onClose;
  }

  get readyState() {
    return this.ws.readyState;
  }

  sendAudio(bytes: ArrayBuffer | Uint8Array): void {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(bytes);
    }
  }

  close(): void {
    this.ws.close();
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
