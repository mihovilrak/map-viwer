import {useEffect, useMemo, useRef, useState} from "react";
import axios from "axios";
import maplibregl, {Map, type StyleSpecification} from "maplibre-gl";

/**
 * Metadata for a geospatial layer.
 */
type LayerMetadata = {
  /** Unique identifier for the layer. */
  id: string;
  /** Human-readable layer name. */
  name: string;
  /** Data provider type (postgis, geopackage, cog, or mbtiles). */
  provider: "postgis" | "geopackage" | "cog" | "mbtiles";
  /** Bounding box in Web Mercator (EPSG:3857) as [minx, miny, maxx, maxy]. */
  bbox?: [number, number, number, number];
};

/**
 * Base URL for the backend API.
 * Reads from VITE_API_BASE_URL environment variable or defaults to current origin.
 */
const apiBase =
  (import.meta.env["VITE_API_BASE_URL"] as string | undefined) ??
  window.location.origin ??
  "http://localhost:8000";

/**
 * Main application component for the map viewer.
 *
 * Displays a list of available layers and renders them on a MapLibre map.
 * Supports both vector (PostGIS) and raster (COG) layers.
 *
 * @returns React component with sidebar and map view.
 */
function App() {
  const mapRef = useRef<Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [layers, setLayers] = useState<LayerMetadata[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mapStyle: StyleSpecification = useMemo(
    () => ({
      version: 8 as const,
      sources: {
        "osm-tiles": {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
        },
      },
      layers: [{id: "osm-base", type: "raster", source: "osm-tiles"}],
    }),
    [],
  );

  useEffect(() => {
    if (containerRef.current && !mapRef.current) {
      mapRef.current = new maplibregl.Map({
        container: containerRef.current,
        style: mapStyle,
        center: [0, 0],
        zoom: 2,
      });
      mapRef.current.addControl(new maplibregl.NavigationControl());
    }
  }, [mapStyle]);

  useEffect(() => {
    axios
      .get(`${apiBase}/api/layers`)
      .then((resp) => setLayers(resp.data))
      .catch((err) => setError(err.message));
  }, []);

  /**
   * Focuses the map on a layer and adds it to the map if not already present.
   *
   * For vector layers: adds vector tile source and fill/line layers.
   * For raster layers: adds raster tile source and raster layer.
   * Zooms the map to the layer's bounding box if available.
   *
   * @param layer - Layer metadata to focus on.
   */
  const focusLayer = (layer: LayerMetadata) => {
    setSelected(layer.id);
    if (!mapRef.current) {
      return;
    }
    const map = mapRef.current;

    if (layer.provider === "postgis") {
      const sourceId = `vector-${layer.name}`;
      if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
          type: "vector",
          tiles: [`${apiBase}/tiles/vector/${layer.name}/{z}/{x}/{y}.pbf`],
        });
        map.addLayer({
          id: `fill-${layer.name}`,
          type: "fill",
          source: sourceId,
          "source-layer": layer.name,
          paint: { "fill-color": "#3b82f6", "fill-opacity": 0.4 },
        });
        map.addLayer({
          id: `line-${layer.name}`,
          type: "line",
          source: sourceId,
          "source-layer": layer.name,
          paint: { "line-color": "#1d4ed8", "line-width": 2 },
        });
      }
    }

    if (layer.provider === "cog") {
      const sourceId = `raster-${layer.id}`;
      if (!map.getSource(sourceId)) {
        map.addSource(sourceId, {
          type: "raster",
          tiles: [`${apiBase}/tiles/raster/${layer.id}/{z}/{x}/{y}.png`],
          tileSize: 256,
        });
        map.addLayer({
          id: `raster-${layer.id}`,
          type: "raster",
          source: sourceId,
          paint: {"raster-opacity": 0.8},
        });
      }
    }

    if (layer.bbox) {
      const [[minx, miny], [maxx, maxy]] = [
        [layer.bbox[0], layer.bbox[1]],
        [layer.bbox[2], layer.bbox[3]],
      ];
      map.fitBounds(
        [
          [minx, miny],
          [maxx, maxy],
        ],
        {padding: 32, animate: true},
      );
    }
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Map Viewer</h1>
        {error && <p className="error">{error}</p>}
        <ul>
          {layers.map((layer) => (
            <li key={layer.id} className={layer.id === selected ? "selected" : ""}>
              <div>
                <strong>{layer.name}</strong> <small>({layer.provider})</small>
              </div>
              <button type="button" onClick={() => focusLayer(layer)}>
                View
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <main ref={containerRef} className="map" />
    </div>
  );
}

export default App;

