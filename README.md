# Map Viewer: Vector & Raster Ingest → Tileserver

FastAPI ingests vector and raster data, stores vectors in PostGIS, converts rasters to COGs, and exposes metadata plus raster XYZ. Vector tiles are served by Tegola (proxy via backend). A minimal React + Vite + TypeScript frontend lists layers and zooms to their extents.

## Quick start (Docker)

1) Copy `.env.example` to `.env` and set credentials.  
2) `docker compose -f infra/docker-compose.yml up --build`  
3) Backend: http://localhost:8000/docs  
4) Tegola tiles: http://localhost:8080/ (map name `mvt`, update config per layer)  
5) Frontend dev server: http://localhost:5173

## Key components

- `backend/`: FastAPI app with upload, ingest, metadata, raster XYZ; PostGIS repository for layers. Python deps managed with `uv`; lint/format via `ruff`; type-check via `pyright`.
- `infra/tegola-config.toml`: Tegola PostGIS provider + template map definition.
- `infra/docker-compose.yml`: PostGIS + Tegola + backend + frontend dev wiring.
- `frontend/`: Vite React TypeScript client (MapLibre) to view vector and raster tiles.
- `PROJECT_STATUS.md`: progress log and checkpoints.

## Local development (Python via uv)

```bash
uv venv
uv pip install -r backend/requirements.txt
uv run ruff check backend
uv run ruff format backend
uv run pytest
uv run pyright  # type checking
```

## Tests

- Backend: `cd backend && pytest` (70% coverage gate via pytest-cov)
- Frontend: `cd frontend && npm test -- --coverage` (Vitest 60% gate)
- Frontend docs: `cd frontend && npm run docs:ts`
- Frontend e2e: `cd frontend && npm run e2e` (requires running app; set `E2E_BASE_URL`)

## Style & quality

- Python: Google Python Style Guide + docstrings; formatted with Black/isort.
- TypeScript: Google style via ESLint + Prettier; strict TS config.
- CI ready: add GitHub Actions per `Instructions.md` when repo is hosted.

