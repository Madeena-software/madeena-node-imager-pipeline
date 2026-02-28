"""Shared pytest configuration for the IPApp backend test suite."""

import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set environment before any app imports
os.environ.setdefault("FLASK_ENV", "testing")
