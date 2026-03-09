#!/usr/bin/env python3
"""XIV Timeline Generator - Entry point script."""

import sys
import os
from pathlib import Path

# Add src to path
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

# Now import and run the CLI
from xiv_timeline.main import app

if __name__ == "__main__":
    app()
