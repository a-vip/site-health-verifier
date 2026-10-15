"""
__main__.py - Entrypoint when running module directly: python -m site_health_verifier
"""
import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
