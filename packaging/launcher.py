"""PyInstaller entry point; imports the application inside its package context."""

from localscribe.app import main

if __name__ == "__main__":
    raise SystemExit(main())
