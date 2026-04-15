/**
 * Tests for components/orb/Orb.tsx
 * Verifies: correct data-state attribute, listening rings, canvas presence.
 */

import { render } from "@testing-library/react"
import Orb from "@/components/orb/Orb"

// Canvas is not supported in jsdom — stub getContext
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = jest.fn().mockReturnValue({
    clearRect: jest.fn(),
    beginPath: jest.fn(),
    arc: jest.fn(),
    stroke: jest.fn(),
    scale: jest.fn(),
    strokeStyle: "",
    lineWidth: 0,
  })
})

describe("Orb component", () => {
  it("renders without crashing", () => {
    const { container } = render(<Orb state="idle" />)
    expect(container.firstChild).not.toBeNull()
  })

  it("applies correct data-state for idle", () => {
    const { container } = render(<Orb state="idle" />)
    const wrapper = container.querySelector("[data-state]")
    expect(wrapper?.getAttribute("data-state")).toBe("idle")
  })

  it("applies correct data-state for listening", () => {
    const { container } = render(<Orb state="listening" />)
    const wrapper = container.querySelector("[data-state]")
    expect(wrapper?.getAttribute("data-state")).toBe("listening")
  })

  it("applies correct data-state for thinking", () => {
    const { container } = render(<Orb state="thinking" />)
    const wrapper = container.querySelector("[data-state]")
    expect(wrapper?.getAttribute("data-state")).toBe("thinking")
  })

  it("applies correct data-state for speaking", () => {
    const { container } = render(<Orb state="speaking" />)
    const wrapper = container.querySelector("[data-state]")
    expect(wrapper?.getAttribute("data-state")).toBe("speaking")
  })

  it("renders ripple rings only in listening state", () => {
    const { container: listeningContainer } = render(<Orb state="listening" />)
    const { container: idleContainer } = render(<Orb state="idle" />)

    // Listening should have ring elements
    const listeningRings = listeningContainer.querySelectorAll("[class*='ring']")
    const idleRings = idleContainer.querySelectorAll("[class*='ring']")

    expect(listeningRings.length).toBeGreaterThan(0)
    expect(idleRings.length).toBe(0)
  })

  it("renders canvas element", () => {
    const { container } = render(<Orb state="speaking" />)
    expect(container.querySelector("canvas")).not.toBeNull()
  })

  it("accepts custom size prop", () => {
    const { container } = render(<Orb state="idle" size={300} />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.style.width).toBe("300px")
    expect(wrapper.style.height).toBe("300px")
  })
})
