"""Reliable launcher for the local ECA Streamlit prototype.

This script may itself be run by any Python installation. It always delegates
to the project virtual environment so global Anaconda packages cannot leak into
the application process.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
APP = ROOT / "app.py"


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def choose_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        if port_is_available(port):
            return port
    raise RuntimeError(f"No available local port found between {preferred} and {preferred + 19}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the ECA prototype using its managed environment.")
    parser.add_argument("--port", type=int, default=8501, help="Preferred port; the next available port is used if occupied.")
    args = parser.parse_args()
    if not VENV_PYTHON.exists():
        print("Project virtual environment not found.", file=sys.stderr)
        print("Run: python3 -m venv .venv", file=sys.stderr)
        print("Then: .venv/bin/python -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    port = choose_port(args.port)
    print(f"Starting ECA Data Request Database at http://localhost:{port}")
    print("Press Ctrl+C to stop the application.")
    command = [
        str(VENV_PYTHON), "-m", "streamlit", "run", str(APP),
        "--server.port", str(port), "--server.headless", "true",
    ]
    try:
        return subprocess.run(command, cwd=ROOT, check=False).returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
