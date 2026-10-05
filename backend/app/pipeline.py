"""새 공지를 가져오는 파이프라인.

수집 → 첨부 추출 순서로 엮는다. 프론트의 "새 공지 가져오기" 버튼이
POST /api/refresh 로 백그라운드에서 돌리고, 손으로는 python -m app.pipeline 으로 돌린다.

요약은 돈이 드는 일이라 여기서 돌리지 않는다. 사용자가 공지에서 요약을 누를 때
그 한 건만 만든다(POST /api/notices/{id}/summary).
각 단계는 앞 단계가 남긴 상태(crawl_state, extract_state)를
보고 자기 몫만 집어 가므로, 중간에 실패해도 다음 실행이 이어서 한다.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from app.crawler.runner import PARSERS, run_source
from app.extract.runner import run as run_extract

log = logging.getLogger(__name__)

# 학부 게시판은 요청 간격이 2.5초라 페이지를 늘리면 그만큼 느려진다.
# 한 번에 새 공지를 놓치지 않을 만큼만 본다.
PAGES = {"kw_main": 2, "cs_dept": 2}

# 출처 키를 사람이 읽을 이름으로. 진행 상황 표시에 쓴다.
SOURCE_LABELS = {"kw_main": "대학 공지", "cs_dept": "학부 공지"}


@dataclass
class PipelineReport:
    started_at: dt.datetime
    crawl: dict[str, str] = field(default_factory=dict)
    extracted: dict[str, int] = field(default_factory=dict)
    new: int = 0
    updated: int = 0
    failed_sources: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"[{self.started_at:%Y-%m-%d %H:%M}] 파이프라인 결과"]
        for key, msg in self.crawl.items():
            lines.append(f"  수집 {key}: {msg}")
        if self.extracted:
            detail = ", ".join(f"{k} {v}" for k, v in sorted(self.extracted.items()))
            lines.append(f"  추출: {detail}")
        return "\n".join(lines)


def run_pipeline(on_stage: Callable[[str], None] | None = None) -> PipelineReport:
    """on_stage 는 단계가 바뀔 때마다 사람이 읽을 문장으로 불린다."""
    stage = on_stage or (lambda _: None)
    report = PipelineReport(started_at=dt.datetime.now())

    for key in PARSERS:
        stage(f"{SOURCE_LABELS.get(key, key)} 수집 중")
        try:
            stats = run_source(key, pages=PAGES.get(key, 1))
        except Exception as exc:  # noqa: BLE001 - 한 출처가 죽어도 나머지는 돈다
            report.crawl[key] = f"실패 ({exc})"
            report.failed_sources.append(key)
            log.exception("수집 실패: %s", key)
            continue

        report.new += stats.new
        report.updated += stats.updated
        note = (
            f"목록 {stats.found} / 신규 {stats.new} / 본문변경 {stats.updated} / "
            f"첨부 {stats.attachments}(불량 {stats.bad_files})"
        )
        if stats.blocked:
            note += " [차단되어 중단]"
            report.failed_sources.append(key)
        report.crawl[key] = note

    stage("첨부파일 읽는 중")
    report.extracted = dict(run_extract())
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # httpx 가 요청마다 INFO 로그를 찍어 결과가 묻힌다.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print(run_pipeline(on_stage=lambda s: print(f"... {s}", flush=True)).render(), flush=True)


if __name__ == "__main__":
    main()
