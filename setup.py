from setuptools import setup, find_packages

setup(
    name="site-health-verifier",
    version="2.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "sitehealth=site_health_verifier.cli:main",
            "site-health-verifier=site_health_verifier.cli:main",
        ],
    },
)
