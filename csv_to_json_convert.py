#!/usr/bin/env python3
"""Backward-compatible entry point for the GhostPost catalog builder.

The original project exposed this filename at repository root. Keep it as a tiny
wrapper so old notes/commands still work while the real implementation lives in
scripts/build_catalog.py.
"""

from scripts.build_catalog import main


if __name__ == "__main__":
    raise SystemExit(main())
