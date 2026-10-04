"""Run the dependency-free Node 22 / Chrome DevTools visual verification."""

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, default=Path("C:/Program Files/Google/Chrome/Application/chrome.exe"))
    args = parser.parse_args()
    subprocess.run(["node", str(ROOT / "scripts/check_html.mjs"), str(args.browser)], check=True, timeout=180)


if __name__ == "__main__":
    main()
