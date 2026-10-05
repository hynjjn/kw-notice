"""하루 한 번 도는 전체 파이프라인.

수집 → 첨부 추출 순서로 엮는다. 요약은 돈이 드는 일이라 자동으로 돌리지 않는다.
사용자가 공지에서 요약을 누를 때 그 한 건만 만든다(POST /api/notices/{id}/summary).
각 단계는 앞 단계가 남긴 상태(crawl_state, extract_state)를
보고 자기 몫만 집어 가므로, 중간에 실패해도 다음 실행이 이어서 한다.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from app.crawler.runner import PARSERS, run_source
from app.extract.runner import run as run_extract

log = logging.getLogger(__name__)

# 학부 게시판은 요청 간격이 2.5초라 페이지를 늘리면 그만큼 느려진다.
# 하루치 새 공지를 놓치지 않을 만큼만 본다.
PAGES = {"kw_main": 2, "cs_dept": 2}


@dataclass
class DailyReport:
    started_at: dt.datetime
    crawl: dict[str, str] = field(default_factory=dict)
    extracted: dict[str, int] = field(default_factory=dict)

    def render(self) -> str:
        lines = [f"[{self.started_at:%Y-%m-%d %H:%M}] 파이프라인 결과"]
        for key, msg in self.crawl.items():
            lines.append(f"  수집 {key}: {msg}")
        if self.extracted:
            detail = ", ".join(f"{k} {v}" for k, v in sorted(self.extracted.items()))
            lines.append(f"  추출: {detail}")
        return "\n".join(lines)


def run_daily() -> DailyReport:
    report = DailyReport(started_at=dt.datetime.now())

    for key in PARSERS:
        try:
            stats = run_source(key, pages=PAGES.get(key, 1))
        except Exception as exc:  # noqa: BLE001 - 한 출처가 죽어도 나머지는 돈다
            report.crawl[key] = f"실패 ({exc})"
            log.exception("수집 실패: %s", key)
            continue

        note = (
            f"목록 {stats.found} / 신규 {stats.new} / 본문변경 {stats.updated} / "
            f"첨부 {stats.attachments}(불량 {stats.bad_files})"
        )
        if stats.blocked:
            note += " [차단되어 중단]"
        report.crawl[key] = note

    report.extracted = dict(run_extract())
    return report
