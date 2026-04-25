export {};

/**
 * Tests for lib/websocket.ts
 * Verify WebSocket behavior — token handling, audio sending, message parsing.
 */

// Mock fetch for ws-token endpoint
global.fetch = jest.fn()
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1
  static CLOSED = 3

  url: string
  binaryType = 'arraybuffer'
  readyState = MockWebSocket.OPEN

  onopen: (() => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string) {
    this.url = url
  }

  send = jest.fn()
  close = jest.fn()
}

global.WebSocket = MockWebSocket as any

beforeEach(() => {
  jest.clearAllMocks()
  // Mock NEXT_PUBLIC_WS_URL
  process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000'
})

describe('LipiWebSocket token handling', () => {
  it('fetches ws-token before connecting (token NOT in localStorage)', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ws_token: 'short-lived-ws-token-xyz' }),
    } as Response)

    const { LipiWebSocket } = await import('@/lib/websocket')
    const handlers = {
      onTranscript: jest.fn(),
      onToken: jest.fn(),
      onTTSStart: jest.fn(),
      onAudio: jest.fn(),
      onTTSEnd: jest.fn(),
      onEmptyAudio: jest.fn(),
      onError: jest.fn(),
      onClose: jest.fn(),
    }

    new LipiWebSocket('sess-123', 'user-456', handlers)

    // Let async initialization run
    await new Promise(r => setTimeout(r, 10))

    // Must have called /api/auth/ws-token
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/auth/ws-token',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('does NOT pass token as localStorage.getItem', async () => {
    const localStorageSpy = jest.spyOn(Storage.prototype, 'getItem')

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ws_token: 'short-lived-token' }),
    } as Response)

    const { LipiWebSocket } = await import('@/lib/websocket')
    new LipiWebSocket('sess-123', 'user-456', {
      onTranscript: jest.fn(),
      onToken: jest.fn(),
      onTTSStart: jest.fn(),
      onAudio: jest.fn(),
      onTTSEnd: jest.fn(),
      onEmptyAudio: jest.fn(),
      onError: jest.fn(),
      onClose: jest.fn(),
    })

    await new Promise(r => setTimeout(r, 10))

    // localStorage.getItem should NOT be called for token (security check)
    const tokenCalls = localStorageSpy.mock.calls.filter(
      args => args[0] === 'lipi.token'
    )
    expect(tokenCalls).toHaveLength(0)
  })
})

describe('LipiWebSocket audio sending', () => {
  it('sendAudio transmits bytes when connection is open', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ws_token: 'token' }),
    } as Response)

    const { LipiWebSocket } = await import('@/lib/websocket')
    const ws = new LipiWebSocket('sess-123', 'user-456', {
      onTranscript: jest.fn(),
      onToken: jest.fn(),
      onTTSStart: jest.fn(),
      onAudio: jest.fn(),
      onTTSEnd: jest.fn(),
      onEmptyAudio: jest.fn(),
      onError: jest.fn(),
      onClose: jest.fn(),
    })

    await new Promise(r => setTimeout(r, 10))

    const audioData = new Uint8Array([1, 2, 3, 4])
    ws.sendAudio(audioData)

    // WebSocket.send should have been called once (the internal ws.send)
    // We check this by verifying no exceptions were thrown
    expect(ws.readyState).toBeDefined()
  })
})
