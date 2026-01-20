#!/usr/bin/env python3
"""
Ledger Scrolls viewer launcher
Usage:
  ./ledger-scrolls               → launch web UI
  ./ledger-scrolls --cli         → command line mode
"""

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--cli", "-c"):
        from src.cli import main as cli_main
        cli_main()
    else:
        from src.ui import main as ui_main
        ui_main()