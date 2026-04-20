# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "torch",
#   "transformers",
#   "sentencepiece",
# ]
# ///
"""Validation probe: zero-shot classify commit subjects (optional `almanac[ml]`).

Re-run after classifier changes to compare distributions. From repo root:

  uv run --extra ml python scripts/probes/probe_zeroshot.py ~/dev/some-repo --n 1000 \\
    --json-out /tmp/some-repo-1000.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from almanac.classifier import classify, clear_cache
from almanac.classifier.zeroshot import (
    MODEL_ID,
    MODEL_REVISION,
    ZEROSHOT_CONFIDENCE_THRESHOLD,
)


def git_log(repo: Path, n: int) -> list[str]:
    out = subprocess.check_output(
        ["git", "log", "--no-merges", f"-n{n}", "--pretty=format:%s"],
        cwd=repo,
        text=True,
    )
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("repo")
    p.add_argument("--n", type=int, default=500)
    p.add_argument(
        "--json-out",
        default=None,
        help="Write combined verb counts and metadata as JSON to this path.",
    )
    args = p.parse_args()

    repo = Path(args.repo).expanduser()
    if not (repo / ".git").exists():
        print(f"ERROR: {repo} is not inside a git repository", file=sys.stderr)
        return 1

    subjects = git_log(repo, args.n)
    print(f"\nRepo: {repo}")
    print(f"Subjects: {len(subjects)}")

    clear_cache()
    t0 = time.time()
    counts: Counter[str] = Counter()
    low_conf: list[tuple[float, str]] = []

    for s in subjects:
        verb, score = classify(s, None, strategy="zeroshot")
        counts[verb] += 1
        if score < 0.5:
            low_conf.append((score, s))

    elapsed = time.time() - t0
    total = sum(counts.values()) or 1
    unclear_share = counts.get("unclear", 0) / total

    print(f"\nClassified {len(subjects)} subjects in {elapsed:.1f}s")
    print("\n=== Distribution ===")
    for v, c in counts.most_common():
        print(f"  {v:>10} {c:>4}  {c / total:>6.1%}")

    print(f"\nUnclear share: {unclear_share:.1%}  (target: ≤15%)")
    if unclear_share <= 0.15:
        print("  PASS ✓")
    else:
        print("  FAIL ✗")

    print("\n=== Lowest-confidence examples (top 15) ===")
    for score, subj in sorted(low_conf)[:15]:
        print(f"  {score:.2f}  {subj[:90]}")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "repo": str(repo.resolve()),
            "n_commits": len(subjects),
            "model": MODEL_ID,
            "revision": MODEL_REVISION,
            "threshold": ZEROSHOT_CONFIDENCE_THRESHOLD,
            "combined_counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "unclear_share": unclear_share,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
