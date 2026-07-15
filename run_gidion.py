"""
PyInstaller entry point.

app/main.py itself can't be used directly as the PyInstaller entry
script -- PyInstaller treats the entry script's own folder as the top
level, so `app` (main.py's own parent folder) isn't importable from
inside main.py once frozen, even though it works fine when running via
`python -m app.main` from source (which adds the project root to
sys.path automatically).

This file sits at the project root instead, so `app` is a proper
sibling package PyInstaller can find. Point PyInstaller here, not at
app/main.py.
"""

from app.main import main

if __name__ == "__main__":
    main()