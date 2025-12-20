import "@testing-library/jest-dom/vitest";
import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {describe, expect, it, vi, beforeEach} from "vitest";

import App from "./App";

const {
  addSource,
  addLayer,
  getSource,
  fitBounds,
  addControl,
  MockMap,
  axiosGet,
} = vi.hoisted(() => {
  const addSource = vi.fn();
  const addLayer = vi.fn();
  const getSource = vi.fn();
  const fitBounds = vi.fn();
  const addControl = vi.fn();

  // Create mock Map constructor
  const MockMap = vi.fn().mockImplementation(() => ({
    addControl,
    addSource,
    addLayer,
    getSource,
    fitBounds,
  }));

  const axiosGet = vi.fn();

  return {
    addSource,
    addLayer,
    getSource,
    fitBounds,
    addControl,
    MockMap,
    axiosGet,
  };
});

vi.mock("maplibre-gl", () => ({
  default: {
    Map: MockMap,
    NavigationControl: vi.fn(),
  },
  Map: MockMap,
  NavigationControl: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {get: axiosGet},
}));

beforeEach(() => {
  addSource.mockReset();
  addLayer.mockReset();
  getSource.mockReset();
  fitBounds.mockReset();
  axiosGet.mockReset();
});

describe("App", () => {
  it("renders header", () => {
    axiosGet.mockResolvedValue({data: []});
    render(<App />);
    expect(screen.getByText(/Map Viewer/)).toBeInTheDocument();
  });

  it("shows error when request fails", async () => {
    axiosGet.mockRejectedValue(new Error("boom"));
    render(<App />);
    await waitFor(() => expect(screen.getByText(/boom/)).toBeInTheDocument());
  });

  it("adds vector source and layers on click", async () => {
    axiosGet.mockResolvedValue({
      data: [{id: "1", name: "demo", provider: "postgis", bbox: [0, 0, 1, 1]}],
    });
    getSource.mockReturnValue(undefined);
    render(<App />);
    await waitFor(() => screen.getByText("demo"));
    fireEvent.click(screen.getByText("View"));
    expect(addSource).toHaveBeenCalledWith("vector-demo", {
      type: "vector",
      tiles: [expect.stringContaining("/tiles/vector/demo/{z}/{x}/{y}.pbf")],
    });
    expect(addLayer).toHaveBeenCalled();
    expect(fitBounds).toHaveBeenCalled();
  });

  it("adds raster source on click", async () => {
    axiosGet.mockResolvedValue({
      data: [{id: "r1", name: "raster", provider: "cog", bbox: [1, 2, 3, 4]}],
    });
    getSource.mockReturnValue(undefined);
    render(<App />);
    await waitFor(() => screen.getByText("raster"));
    fireEvent.click(screen.getByText("View"));
    expect(addSource).toHaveBeenCalledWith("raster-r1", {
      type: "raster",
      tiles: [expect.stringContaining("/tiles/raster/r1/{z}/{x}/{y}.png")],
      tileSize: 256,
    });
  });
});

