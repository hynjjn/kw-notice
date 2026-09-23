from __future__ import annotations

import argparse
import logging

from app.summarize import digest as digest_mod
from app.summarize.runner import run


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.summarize")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--force", action="store_true", help="이미 요약된 것도 다시")
    p.add_argument("--dry-run", action="store_true", help="API 호출 없이 대상만 확인")
    p.add_argument("--digest", metavar="YYYY-MM-DD", help="그날의 하루치 요약을 만든다")
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    if args.digest:
        import datetime as dt

        result = digest_mod.build(dt.date.fromisoformat(args.digest), dry_run=args.dry_run)
        if result:
            print(result.summary_md)
        return

    stats = run(limit=args.limit, force=args.force, dry_run=args.dry_run)

    if args.dry_run:
        return

    print(
        f"요약 {stats.done} / 실패 {stats.failed} / 건너뜀 {stats.skipped}\n"
        f"토큰 입력 {stats.input_tokens:,} (캐시 {stats.cache_read:,}) "
        f"출력 {stats.output_tokens:,}"
    )
    for err in stats.errors[:5]:
        print(f"  실패: {err}")


if __name__ == "__main__":
    main()
