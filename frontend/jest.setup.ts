import '@testing-library/jest-dom'

HTMLCanvasElement.prototype.getContext = jest.fn().mockReturnValue({
  clearRect: jest.fn(),
  beginPath: jest.fn(),
  arc: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  stroke: jest.fn(),
  scale: jest.fn(),
  strokeStyle: "",
  lineWidth: 0,
  lineCap: "round",
})
