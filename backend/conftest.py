"""Pytest configuration to expose the backend package for imports."""

import sys
from pathlib import Path


# Add the project root (parent of backend/) to sys.path so 'backend' can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
