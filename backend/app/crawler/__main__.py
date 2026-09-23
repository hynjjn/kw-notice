from __future__ import annotations

import argparse
import logging

from app.crawler.runner import PARSERS, run_source


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.crawler")
    p.add_argument("source", choices=sorted(PARSERS))
    p.add_argument("--pages", type=int, default=1, help="훑을 목록 페이지 수")
    p.add_argument("--limit", type=int, default=None, help="처리할 공지 수 제한(테스트용)")
    p.add_argument("--no-detail", action="store_true", help="목록만 수집")
    p.add_argument("--no-download", action="store_true", help="첨부를 내려받지 않음")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    stats = run_source(
        args.source,
        pages=args.pages,
        limit=args.limit,
        fetch_detail=not args.no_detail,
        download=not args.no_download,
    )
    print(
        f"목록 {stats.found}건 / 신규 {stats.new} / 본문변경 {stats.updated} / "
        f"상세수집 {stats.detail_fetched} / 첨부 {stats.attachments}"
        f"(불량 {stats.bad_files}) / 실패 {stats.failed}"
    )
    if stats.blocked:
        raise SystemExit("출처가 요청을 막아 중간에 멈췄다. crawl_runs 를 확인할 것.")


if __name__ == "__main__":
    main()
