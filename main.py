"""CLI entry point for BioAgent-Discovery."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from bioagent.graph import run_pipeline


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Multi-agent early-stage drug-discovery research workflow")
    parser.add_argument("--disease", "-d", required=True, help="Disease to research")
    parser.add_argument("--output", "-o", default="reports/discovery_report.md", help="Markdown output path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print pipeline diagnostics")
    return parser.parse_args()


def main() -> int:
    """Execute workflow and persist its Markdown report."""
    load_dotenv()
    args = parse_args()
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env before running.", file=sys.stderr)
        return 2
    result = run_pipeline(args.disease)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.get("final_report") or "# No report generated\n", encoding="utf-8")
    print(f"Report written to {output}")
    if args.verbose:
        print(f"Target: {result.get('target_protein', 'N/A')}")
        print(f"Candidates: {len(result.get('candidate_molecules', []))}")
        if result.get("errors"):
            print("Warnings:")
            for error in result["errors"]:
                print(f"- {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
