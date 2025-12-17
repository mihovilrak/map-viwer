# Project Status

## Decisions
- Vector tiles served via Tegola pointing at PostGIS; FastAPI proxies metadata and ingress.
- Raster tiles generated on the fly from COGs via rio-tiler.
- Frontend uses React + Vite + TypeScript with MapLibre.

## Milestones
- [x] Create project skeleton and configs.
- [x] Implement ingestion pipeline wired to PostGIS with metadata persistence.
- [ ] Wire Tegola map definitions to uploaded layers (template provided, needs per-layer map).
- [x] Raster COG ingestion and XYZ endpoint.
- [x] Frontend layer list + zoom-to-bbox and tile overlays.
- [ ] CI pipeline (lint + test) and sample datasets.
- [ ] Add automated Tegola map generation aligned with ingested layers.

## Notes
- Follow Google Style Guide for Python docstrings and TS linting.
- Keep `Instructions.md` aligned with actual endpoints as they evolve.
- Tegola config shipped as template; add per-layer map entries or generation script as layers are ingested.
- Python tooling now standardized on uv (env/install), ruff (lint+format), pyright (types). TypeScript docs via tdoc.
