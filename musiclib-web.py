#!/usr/bin/env python3
"""
Convenience launcher for the MusicWeb Streamlit app.

Usage:
  python3 musiclib-web.py

This runs Streamlit pointing at the main app module under
musicweb/src/musicweb/web/app.py.
"""

import sys, os

try:
    from streamlit.web import cli as stcli
except Exception as e:
    print("Streamlit is not installed. Install it with: pip install streamlit")
    raise


def main() -> int:
    # Ensure local package path is available
    repo_root = os.path.dirname(os.path.abspath(__file__))
    pkg_src = os.path.join(repo_root, "musicweb", "src")
    if pkg_src not in sys.path:
        sys.path.insert(0, pkg_src)
    sys.argv = [
        "streamlit",
        "run",
        "musicweb/src/musicweb/web/app.py",
        "--server.port",
        "8501",
    ]
    return stcli.main()


if __name__ == "__main__":
    raise SystemExit(main())
