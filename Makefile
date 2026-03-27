.PHONY: backend
backend:
	@echo "Starting backend (from repo root)..."
	@if [ -x .venv/bin/python3 ]; then .venv/bin/python3 backend/app.py; else python3 backend/app.py; fi
