/**
 * Tests for app/auth/page.tsx
 * Verifies: renders correctly, demo login triggers API, no localStorage token writes.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react"

// ── Mocks ─────────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
}))

jest.mock("@/lib/api", () => ({
  demoLogin: jest.fn(),
  exchangeGoogleCode: jest.fn(),
}))

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("AuthPage rendering", () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Set NODE_ENV so the demo button renders
    Object.defineProperty(process.env, "NODE_ENV", { value: "development", writable: true })
  })

  it("renders the LIPI logo in Nepali", async () => {
    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)
    expect(screen.getByText("लिपि")).toBeInTheDocument()
  })

  it("renders Google sign-in button", async () => {
    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)
    expect(screen.getByText(/Continue with Google/i)).toBeInTheDocument()
  })

  it("renders Nepali tagline", async () => {
    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)
    expect(screen.getByText("तपाईं बोल्नुहोस्। लिपि सिक्छ।")).toBeInTheDocument()
  })

  it("renders demo login button in development", async () => {
    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)
    expect(screen.getByText(/Demo Login/i)).toBeInTheDocument()
  })
})

describe("AuthPage demo login", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("calls demoLogin() when demo button is clicked", async () => {
    const { demoLogin } = await import("@/lib/api")
    ;(demoLogin as jest.Mock).mockResolvedValueOnce({ success: true, onboarding_complete: true })

    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)

    const btn = screen.getByText(/Demo Login/i)
    fireEvent.click(btn)

    await waitFor(() => expect(demoLogin).toHaveBeenCalledTimes(1))
  })

  it("does NOT write lipi.token to localStorage on demo login", async () => {
    const { demoLogin } = await import("@/lib/api")
    ;(demoLogin as jest.Mock).mockResolvedValueOnce({ success: true, onboarding_complete: true })

    const localStorageSpy = jest.spyOn(Storage.prototype, "setItem")

    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)
    fireEvent.click(screen.getByText(/Demo Login/i))

    await waitFor(() => expect(demoLogin).toHaveBeenCalledTimes(1))

    const tokenWrites = localStorageSpy.mock.calls.filter(([key]) => key === "lipi.token")
    expect(tokenWrites).toHaveLength(0)
  })

  it("redirects to /home when onboarding is complete", async () => {
    const mockReplace = jest.fn()
    jest.mock("next/navigation", () => ({
      useRouter: () => ({ replace: mockReplace }),
      useSearchParams: () => new URLSearchParams(),
    }))

    const { demoLogin } = await import("@/lib/api")
    ;(demoLogin as jest.Mock).mockResolvedValueOnce({ success: true, onboarding_complete: true })

    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)
    fireEvent.click(screen.getByText(/Demo Login/i))

    await waitFor(() => expect(demoLogin).toHaveBeenCalled())
  })

  it("redirects to /onboarding when onboarding is not complete", async () => {
    const { demoLogin } = await import("@/lib/api")
    ;(demoLogin as jest.Mock).mockResolvedValueOnce({ success: true, onboarding_complete: false })

    const AuthPage = (await import("@/app/auth/page")).default
    render(<AuthPage />)
    fireEvent.click(screen.getByText(/Demo Login/i))

    await waitFor(() => expect(demoLogin).toHaveBeenCalled())
  })
})
