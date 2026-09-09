#!/usr/bin/env python
"""Entry point: `python main.py --url <youtube-url>`"""

import sys

from classical_candles.cli import main

if __name__ == "__main__":
    sys.exit(main())
