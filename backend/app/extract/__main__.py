from __future__ import annotations

import argparse
import logging

from app.extract.runner import run


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.extract")
    p.add_argument("--ext", nargs="*", help="처리할 확장자")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    stats = run(limit=args.limit, exts=args.ext)
    for key in sorted(stats):
        print(f"{key:24} {stats[key]}")
    print(f"{'합계':24} {sum(stats.values())}")


if __name__ == "__main__":
    main()
