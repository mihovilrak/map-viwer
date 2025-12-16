#!/usr/bin/env bash
set -euo pipefail

# Usage: ./tools/make_cog.sh input.tif output_cog.tif

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <input.tif> <output_cog.tif>"
  exit 1
fi

INPUT="$1"
OUTPUT="$2"

gdal_translate -of COG -co COMPRESS=LZW "$INPUT" "$OUTPUT"
echo "Created COG at $OUTPUT"

