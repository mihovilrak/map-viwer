import axios from "axios";
import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";

import App from "./App";

const addSource = vi.fn();
const addLayer = vi.fn();
const getSource = vi.fn().mockReturnValue(undefined);
const fitBounds = vi.fn();

vi.mock("maplibre-gl", () => ({
  default: vi.fn().mockImplementation(() => ({
    addControl: vi.fn(),
    addSource,
    addLayer,
    getSource,
    fitBounds,
  })),
  NavigationControl: vi.fn(),
}));

vi.mock("axios", () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockedAxios = vi.mocked(axios, {deep: true});

describe("App interactions", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getSource.mockReturnValue(undefined);
    mockedAxios.get.mockReset();
  });

  it("adds vector layer source on click", async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: [{id: "1", name: "roads", provider: "postgis"}],
    });
    render(<App />);

    await waitFor(() => screen.getByText(/roads/i));
    fireEvent.click(screen.getByText(/View/i));

    await waitFor(() => expect(addSource).toHaveBeenCalled());
    expect(addLayer).toHaveBeenCalled();
  });

  it("adds raster source on click", async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: [{id: "2", name: "r1", provider: "cog"}],
    });
    render(<App />);

    await waitFor(() => screen.getByText(/r1/i));
    fireEvent.click(screen.getByText(/View/i));

    await waitFor(() => expect(addSource).toHaveBeenCalled());
  });
});

