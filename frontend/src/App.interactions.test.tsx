import axios from "axios";
import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";

import App from "./App";

const {addSource, addLayer, getSource, fitBounds, addControl, MockMap} = vi.hoisted(() => {
  const addSource = vi.fn();
  const addLayer = vi.fn();
  const getSource = vi.fn().mockReturnValue(undefined);
  const fitBounds = vi.fn();
  const addControl = vi.fn();

  // Create mock Map constructor as a class
  class MockMapClass {
    addControl = addControl;
    addSource = addSource;
    addLayer = addLayer;
    getSource = getSource;
    fitBounds = fitBounds;
  }

  const MockMap = vi.fn().mockImplementation(() => new MockMapClass());

  return {addSource, addLayer, getSource, fitBounds, addControl, MockMap};
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
  default: {
    get: vi.fn(),
  },
}));

const mockedAxios = vi.mocked(axios, {deep: true});

describe("App interactions", () => {
  beforeEach(() => {
    // Reset individual mocks instead of all mocks to preserve MockMap implementation
    addSource.mockReset();
    addLayer.mockReset();
    getSource.mockReset().mockReturnValue(undefined);
    fitBounds.mockReset();
    addControl.mockReset();
    mockedAxios.get.mockReset();
  });

  it("adds vector layer source on click", async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: [{id: "1", name: "roads", provider: "postgis"}],
    });
    render(<App />);

    await waitFor(() => screen.getByText(/roads/i));
    const viewButton = screen.getByRole("button", {name: /View/i});
    fireEvent.click(viewButton);

    await waitFor(() => expect(addSource).toHaveBeenCalled());
    expect(addLayer).toHaveBeenCalled();
  });

  it("adds raster source on click", async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: [{id: "2", name: "r1", provider: "cog"}],
    });
    render(<App />);

    await waitFor(() => screen.getByText(/r1/i));
    const viewButton = screen.getByRole("button", {name: /View/i});
    fireEvent.click(viewButton);

    await waitFor(() => expect(addSource).toHaveBeenCalled());
  });
});

