"""Pytest configuration to expose the backend package for imports."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_PATH = PROJECT_ROOT

if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

