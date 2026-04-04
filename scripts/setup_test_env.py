"""Helper to create a local .env file with dummy keys for running tests locally.

Usage: python scripts/setup_test_env.py --yes
This will create a .env file with safe dummy values for optional providers used in tests.
"""

import argparse
from pathlib import Path

ENV_CONTENT = """
# Local test environment (safe dummy values)
ODDS_API_KEY=CI_DUMMY_ODDS_KEY
API_FOOTBALL_KEY=CI_DUMMY_API_FOOTBALL_KEY
FOOTBALL_DATA_API_KEY=CI_DUMMY_FOOTBALL_DATA_KEY
# To enable live network tests set RUN_NETWORK_TESTS=1 (not recommended in CI)
RUN_NETWORK_TESTS=0
"""

if __name__ == "__main__":
    p = Path(".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    if p.exists():
        print(".env already exists; not overwriting")
    else:
        if not args.yes:
            resp = input("Create .env with dummy keys for testing? [y/N] ")
            if resp.lower() != "y":
                print("Aborted")
                raise SystemExit(1)
        p.write_text(ENV_CONTENT)
        print("Created .env with dummy test keys")
