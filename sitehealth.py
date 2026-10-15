#!/usr/bin/env python3
"""
sitehealth.py - Direct standalone runner for Site Health Verifier.
Run directly without installing: python sitehealth.py https://your-site.com
"""
import sys
from site_health_verifier.cli import main

if __name__ == "__main__":
    sys.exit(main())
