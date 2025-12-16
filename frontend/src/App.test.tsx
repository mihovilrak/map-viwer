import {render, screen} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";

import App from "./App";

vi.mock("maplibre-gl", () => ({
  default: vi.fn().mockImplementation(() => ({
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    getSource: vi.fn(),
    fitBounds: vi.fn(),
  })),
  NavigationControl: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {
    get: vi.fn().mockResolvedValue({data: []}),
  },
}));

describe("App", () => {
  it("renders header", () => {
    render(<App />);
    expect(screen.getByText(/Map Viewer/)).toBeInTheDocument();
  });
});

