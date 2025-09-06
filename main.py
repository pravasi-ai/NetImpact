#!/usr/bin/env python3
"""
Main entry point for Network Configuration Impact Analysis Platform CLI.
Provides complete interface for data ingestion and impact analysis.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from cli.main import cli

if __name__ == "__main__":
    cli()
