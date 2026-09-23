"""cron 스케줄러.

기본은 매일 07:00(Asia/Seoul)에 한 번. 공지는 업무 시작 시각에 몰려 올라오므로
아침에 한 번 돌면 전날 것과 당일 이른 것이 함께 잡힌다.
"""

from __future__ import annotations

import argparse
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.pipeline import run_daily

log = logging.getLogger(__name__)

TIMEZONE = "Asia/Seoul"
DEFAULT_HOUR = 7


def job() -> None:
    report = run_daily()
    print(report.render(), flush=True)


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.scheduler")
    p.add_argument("--hour", type=int, default=DEFAULT_HOUR)
    p.add_argument("--minute", type=int, default=0)
    p.add_argument("--now", action="store_true", help="스케줄 없이 한 번만 즉시 실행")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # httpx 가 요청마다 INFO 로그를 찍어 결과가 묻힌다.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.now:
        job()
        return

    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        job,
        CronTrigger(hour=args.hour, minute=args.minute, timezone=TIMEZONE),
        id="daily",
        max_instances=1,
        # 서버가 잠들었다 깨어나면 지난 실행을 한 번은 따라잡는다.
        misfire_grace_time=3600,
        coalesce=True,
    )
    print(f"매일 {args.hour:02d}:{args.minute:02d} ({TIMEZONE}) 실행. Ctrl+C 로 종료.")
    scheduler.start()


if __name__ == "__main__":
    main()
