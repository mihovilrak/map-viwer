# Map Viewer Backend

FastAPI backend service for ingesting, storing, and serving geospatial vector and raster data. Handles file uploads, transforms geometries to EPSG:3857 (Web Mercator), stores vectors in PostGIS, converts rasters to Cloud Optimized GeoTIFFs (COGs), and serves tile endpoints for both vector and raster layers.

## Overview

The backend provides:
- **File Upload & Ingestion**: Accepts vector (GeoJSON, Shapefile, GeoPackage) and raster (GeoTIFF) files
- **Coordinate Transformation**: Transforms all geometries to EPSG:3857 at ingestion time
- **PostGIS Storage**: Stores vector layers in PostGIS database
- **COG Generation**: Converts raster files to Cloud Optimized GeoTIFF format
- **Tile Serving**: Proxies vector tiles from Tegola and generates raster tiles from COGs using rio-tiler
- **Layer Metadata**: REST API for querying layer information and bounding boxes

## Project Structure

```
backend/
├── app/
│   ├── api/              # FastAPI route handlers
│   │   ├── ingest.py     # File upload and ingestion endpoints
│   │   ├── layers.py     # Layer metadata endpoints
│   │   └── tiles.py      # Vector/raster tile serving endpoints
│   ├── core/
│   │   └── config.py     # Settings and configuration management
│   ├── db/
│   │   ├── database.py   # Repository pattern for layer metadata
│   │   └── models.py      # Database models and schemas
│   ├── services/         # Business logic layer
│   │   ├── ingest_raster.py  # Raster ingestion service
│   │   ├── ingest_vector.py  # Vector ingestion service
│   │   └── tiles_postgis.py  # PostGIS tile utilities
│   ├── utils/
│   │   └── gdal_helpers.py   # GDAL/ogr2ogr utilities
│   └── main.py           # FastAPI application entrypoint
├── tests/                # Test suite (pytest)
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container image definition
└── conftest.py          # Pytest configuration
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for package management
- PostgreSQL with PostGIS extension
- GDAL/OGR tools (ogr2ogr, gdal_translate, gdalwarp)
- Tegola service (for vector tiles)

### Installation

1. Create a virtual environment using `uv`:
```bash
cd backend
uv venv
```

2. Activate the virtual environment:
```bash
# On Windows (PowerShell)
.venv\Scripts\Activate.ps1

# On Unix/macOS
source .venv/bin/activate
```

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Copy .env.example to .env and configure
# Required variables:
# - DATABASE_URL: PostgreSQL connection string
# - TEGOLA_BASE_URL: Tegola service URL (default: http://localhost:8080)
# - ALLOW_ORIGINS: CORS allowed origins (comma-separated)
# - UPLOAD_DIR: Directory for temporary file uploads
# - MAX_UPLOAD_SIZE: Maximum file size in bytes (default: 536870912 = 512MB)
```

5. Run the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## API Endpoints

### Health Check
- `GET /health` - Service health check endpoint

### Layer Management
- `GET /api/layers` - List all registered layers
- `GET /api/layers/{layer_id}/bbox` - Get bounding box for a specific layer

### File Upload & Ingestion
- `POST /api/layers/upload` - Upload a geospatial file (vector or raster)
- `POST /api/layers/ingest/{upload_id}` - Ingest an uploaded file
  - Query parameters:
    - `kind`: `"vector"` or `"raster"`
    - `layer_name`: Name for the layer (required for vector)

### Tile Serving
- `GET /tiles/vector/{layer_name}/{z}/{x}/{y}.pbf` - Vector tile (MVT format, proxied from Tegola)
- `GET /tiles/raster/{layer_id}/{z}/{x}/{y}.png` - Raster tile (PNG format, generated from COG)

## Development

### Code Quality

The project uses:
- **ruff**: Formatting and linting (replaces Black/isort)
- **ty**: Type checking (NOT mypy)
- **pytest**: Unit and e2e testing

Run code quality checks:
```bash
# Format code
uv run ruff format backend

# Check formatting
uv run ruff check --fix backend

# Type checking
uv run ty check
```

### Testing

Run the test suite:
```bash
cd backend
pytest
```

Run with coverage (70% threshold):
```bash
pytest --cov=app --cov-report=term-missing
```

### Code Style

- Follow [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- Use Google-style docstrings for all functions, classes, and modules
- Type hints are required for function parameters and return values
- Use dependency injection via FastAPI `Depends()` for testability

## Architecture Patterns

### Repository Pattern
Layer metadata is abstracted through `LayerRepositoryProtocol`, allowing for:
- `PostgresLayerRepository`: Production implementation using PostgreSQL
- `InMemoryLayerRepository`: Testing implementation using in-memory storage

### Service Layer
Business logic is separated into service modules:
- API handlers delegate to service modules
- Services are testable independently of FastAPI
- Services handle coordinate transformations and file processing

### Dependency Injection
- Settings are injected via `config.get_settings()`
- Repositories are injected via FastAPI `Depends()`
- This pattern enables easy testing with mock dependencies

## Critical Requirements

⚠️ **IMPORTANT**: All coordinate transformations happen at ingestion time, not runtime.

- **Vector ingestion**: MUST use `-t_srs EPSG:3857` in ogr2ogr commands
- **Raster ingestion**: MUST transform to EPSG:3857 before COG creation
- All geometries stored in PostGIS must be in EPSG:3857
- All bounding boxes returned by the API are in EPSG:3857

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `TEGOLA_BASE_URL` | Tegola service URL | `http://localhost:8080` |
| `ALLOW_ORIGINS` | CORS allowed origins (comma-separated) | `http://localhost:5173` |
| `UPLOAD_DIR` | Temporary upload directory | `/tmp/uploads` |
| `MAX_UPLOAD_SIZE` | Maximum file size in bytes | `536870912` (512MB) |

## Dependencies

Key dependencies:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `psycopg2`: PostgreSQL adapter
- `pydantic` / `pydantic-settings`: Settings and validation
- `rio-tiler`: Raster tile generation from COGs
- `pytest` / `pytest-cov`: Testing framework
- `ruff`: Code formatting and linting
- `ty`: Type checking

See `requirements.txt` for complete list.

## Docker

Build and run with Docker:
```bash
docker build -t map-viewer-backend .
docker run -p 8000:8000 --env-file .env map-viewer-backend
```

Or use `docker-compose` from the project root (see main README.md).

## Troubleshooting

### GDAL/OGR not found
Ensure GDAL tools are installed and available in PATH:
- Windows: Install via OSGeo4W or conda
- Linux: `apt-get install gdal-bin` or `yum install gdal`
- macOS: `brew install gdal`

### PostGIS connection errors
Verify:
- PostgreSQL is running
- PostGIS extension is installed: `CREATE EXTENSION postgis;`
- `DATABASE_URL` is correctly formatted
- Database user has necessary permissions

### Coordinate system issues
All geometries must be transformed to EPSG:3857 at ingestion. Verify:
- Vector ingestion uses `-t_srs EPSG:3857` in ogr2ogr
- Raster ingestion transforms to EPSG:3857 before COG creation
- Check layer SRID after ingestion matches 3857

