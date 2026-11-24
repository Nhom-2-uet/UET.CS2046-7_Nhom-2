"""Entry point: start the Streamlit expense assistant interface."""

import subprocess
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = APP_DIR / "frontend"
PROJECT_DIR = APP_DIR.parents[1]
VENV_PYTHON = PROJECT_DIR / "venv" / "Scripts" / "python.exe"


def main() -> int:
    """Run Streamlit from the project venv when it is available."""
    python_executable = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)
    return subprocess.call(
        [str(python_executable), "-m", "streamlit", "run", "app.py"],
        cwd=FRONTEND_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
