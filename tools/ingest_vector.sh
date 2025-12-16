#!/usr/bin/env bash
set -euo pipefail

# Usage: ./tools/ingest_vector.sh input.geojson my_layer
# Requires GDAL/OGR installed and DATABASE_URL env var set.

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <vector_file> <layer_name>"
  exit 1
fi

INPUT="$1"
LAYER="$2"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL env var is required (e.g., postgresql://gis:gis@localhost:5432/gis)"
  exit 1
fi

ogr2ogr -f "PostgreSQL" "$DATABASE_URL" "$INPUT" -nln "$LAYER" -lco GEOMETRY_NAME=geom -overwrite
echo "Ingested $INPUT into $LAYER"

