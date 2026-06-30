#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys

from reconcile_opsd.gpu_utils import gpu_report, query_gpu_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Report GPU state and choose a low-conflict CUDA device.")
    parser.add_argument("--min-free-mb", type=int, default=20_000)
    parser.add_argument("--max-used-mb", type=int, default=70_000)
    parser.add_argument("--export", action="store_true", help="Print only an export command for CUDA_VISIBLE_DEVICES.")
    args = parser.parse_args()

    rows = query_gpu_status()
    report = gpu_report(rows, min_free_mb=args.min_free_mb, max_used_mb=args.max_used_mb)
    selected = report["selected_gpu"]
    if args.export:
        if not selected:
            print("# no GPU matched selection policy", file=sys.stderr)
            raise SystemExit(1)
        print(f"export CUDA_VISIBLE_DEVICES={selected['index']}")
        return

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not selected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
