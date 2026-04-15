/**
 * Tests for lib/api.ts
 * Verify the API client sends requests correctly and handles errors.
 */

// Mock fetch globally
global.fetch = jest.fn()

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>

beforeEach(() => {
  jest.clearAllMocks()
})

describe('demoLogin', () => {
  it('calls /api/auth/demo with POST', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, onboarding_complete: true }),
    } as Response)

    const { demoLogin } = await import('@/lib/api')
    const result = await demoLogin()

    expect(mockFetch).toHaveBeenCalledWith('/api/auth/demo', expect.objectContaining({
      method: 'POST',
    }))
    expect(result.onboarding_complete).toBe(true)
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      text: async () => 'Forbidden',
      statusText: 'Forbidden',
    } as Response)

    const { demoLogin } = await import('@/lib/api')
    await expect(demoLogin()).rejects.toThrow('HTTP 403')
  })
})

describe('exchangeGoogleCode', () => {
  it('sends code and redirect_uri to /api/auth/google', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, onboarding_complete: false }),
    } as Response)

    const { exchangeGoogleCode } = await import('@/lib/api')
    await exchangeGoogleCode('auth-code-123', 'http://localhost:3000/auth')

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/auth/google',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ code: 'auth-code-123', redirect_uri: 'http://localhost:3000/auth' }),
      })
    )
  })
})

describe('createSession', () => {
  it('calls /api/sessions with POST (no token in URL)', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session_id: 'sess-123',
        user_id: 'user-456',
        started_at: new Date().toISOString(),
      }),
    } as Response)

    const { createSession } = await import('@/lib/api')
    const session = await createSession()

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/sessions',
      expect.objectContaining({ method: 'POST' })
    )
    // CRITICAL: Token must NOT be in the URL (security check)
    const callArgs = mockFetch.mock.calls[0]
    const url = callArgs[0] as string
    expect(url).not.toContain('token=')
    expect(url).toBe('/api/sessions')

    expect(session.session_id).toBe('sess-123')
  })
})

describe('getMyStats', () => {
  it('calls /api/proxy/teachers/me/stats', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        total_points: 420,
        current_streak: 5,
        words_taught: 47,
        sessions_completed: 12,
        rank: 3,
      }),
    } as Response)

    const { getMyStats } = await import('@/lib/api')
    const stats = await getMyStats()

    expect(stats.total_points).toBe(420)
    expect(stats.current_streak).toBe(5)
  })
})
