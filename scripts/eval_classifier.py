"""Dev-only: report rules-classifier coverage on any repo+window.

Not shipped in the wheel. Not importable from `almanac`. Read-only.

Usage:
    python scripts/eval_classifier.py /path/to/repo --year 2025
    python scripts/eval_classifier.py /path/to/repo --since 2024-01-01 --until 2024-12-31
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from almanac.classifier import rules  # noqa: E402
from almanac.classifier.preprocess import preprocess  # noqa: E402
from almanac.ingest import iter_commits  # noqa: E402
from almanac.window import resolve_window  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--since", default=None)
    parser.add_argument("--until", default=None)
    parser.add_argument(
        "--unclear-samples",
        type=int,
        default=20,
        help="How many random unclear subjects to print (default 20)",
    )
    args = parser.parse_args()

    if not (args.repo / ".git").exists():
        print(f"error: {args.repo} is not a git repo", file=sys.stderr)
        return 2

    window = resolve_window(args.year, args.since, args.until)

    t0 = time.perf_counter()
    commits = list(iter_commits(args.repo, window))
    t_ingest = time.perf_counter() - t0

    t1 = time.perf_counter()
    counts: Counter[str] = Counter()
    unclear_subjects: list[str] = []
    for c in commits:
        clean = preprocess(c.subject)
        verb, _ = rules.classify_commit(clean, None)
        counts[verb] += 1
        if verb == "unclear":
            unclear_subjects.append(c.subject)
    t_classify = time.perf_counter() - t1

    total = sum(counts.values())
    unclear = counts.get("unclear", 0)
    unclear_rate = (100 * unclear / total) if total else 0.0

    print(f"Repo:         {args.repo}")
    print(f"Window:       {window.label}")
    print(f"Total:        {total}")
    print(f"Ingest time:  {t_ingest * 1000:.0f} ms")
    print(f"Classify time:{t_classify * 1000:.0f} ms")
    print(f"Unclear rate: {unclear_rate:.1f}% ({unclear}/{total})")
    print()
    print("Breakdown:")
    for verb, n in counts.most_common():
        pct = 100 * n / total if total else 0
        print(f"  {verb:10s} {n:5d}  {pct:5.1f}%")

    if unclear_subjects and args.unclear_samples > 0:
        sample_n = min(args.unclear_samples, len(unclear_subjects))
        rng = random.Random(42)
        sample = rng.sample(unclear_subjects, sample_n)
        print()
        print(
            f"Unclear samples ({sample_n} of {len(unclear_subjects)}, "
            "post-preprocess shown in brackets when different):"
        )
        for s in sample:
            clean = preprocess(s)
            if clean != s:
                print(f"  {s[:90]}  [{clean[:80]}]")
            else:
                print(f"  {s[:100]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
