"""Entry point used by `python yt.py` and by the PyInstaller build."""

import sys

from ytcli.ui.cli import main

if __name__ == "__main__":
    sys.exit(main())
