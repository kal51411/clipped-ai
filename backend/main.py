#!/usr/bin/env python3
"""
Direct backend entrypoint.
Auto-detects backend/venv and re-executes with the correct interpreter if run with system python.
"""
import os
import sys

# Locate backend/venv
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(CURRENT_DIR, "venv")
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")

if os.path.exists(VENV_PYTHON) and sys.prefix != VENV_DIR:
    os.environ["VIRTUAL_ENV"] = VENV_DIR
    os.environ["PATH"] = os.path.join(VENV_DIR, "bin") + os.path.pathsep + os.environ.get("PATH", "")
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
