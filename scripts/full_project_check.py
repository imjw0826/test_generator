#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Study Question Generator full project checks.")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend lint and typecheck.")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip end-to-end backend workflow smoke test.")
    args = parser.parse_args()

    commands: list[tuple[str, list[str], Path]] = [
        ("Backend tests", [str(ROOT / "backend" / ".venv" / "bin" / "python"), "-m", "pytest", "tests/", "-v"], ROOT / "backend"),
    ]

    if not args.skip_smoke:
        commands.append((
            "Full workflow smoke",
            [str(ROOT / "backend" / ".venv" / "bin" / "python"), str(ROOT / "scripts" / "workflow_smoke.py")],
            ROOT,
        ))

    if not args.skip_frontend:
        commands.extend([
            ("Frontend lint", ["npm", "run", "lint"], ROOT / "frontend"),
            ("Frontend typecheck", ["npx", "tsc", "--noEmit"], ROOT / "frontend"),
        ])

    for label, command, cwd in commands:
        print(f"\n==> {label}")
        result = subprocess.run(command, cwd=cwd)
        if result.returncode != 0:
            print(f"\nFAILED: {label}", file=sys.stderr)
            return result.returncode

    print("\nAll project checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
