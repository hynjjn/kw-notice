"""프론트의 "새 공지 가져오기" 버튼이 돌리는 백그라운드 작업.

수집은 학교 서버에 요청 간격을 두고 도느라 몇 분 걸린다. HTTP 요청 하나로
붙잡고 있을 수 없으니 스레드로 돌리고, 프론트는 상태를 주기적으로 묻는다.

한 번에 하나만 돈다. 두 번 눌러도 학교 서버를 두 배로 두드리지 않는다.
상태는 프로세스 메모리에만 있다. uvicorn worker 를 여러 개 띄우면 worker 마다
따로 돌 수 있으니, 배포에서는 worker 를 하나로 두거나 DB 잠금으로 바꿔야 한다.
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
from dataclasses import dataclass, field, replace
from typing import Literal

from app.pipeline import run_pipeline

log = logging.getLogger(__name__)

State = Literal["idle", "running", "done", "failed"]


@dataclass(frozen=True)
class RefreshStatus:
    state: State = "idle"
    stage: str | None = None
    started_at: dt.datetime | None = None
    finished_at: dt.datetime | None = None
    new: int = 0
    updated: int = 0
    failed_sources: list[str] = field(default_factory=list)
    error: str | None = None


_lock = threading.Lock()
_status = RefreshStatus()


def status() -> RefreshStatus:
    return _status


def _set(**changes) -> None:
    global _status
    with _lock:
        _status = replace(_status, **changes)


def start() -> RefreshStatus:
    """작업을 시작한다. 이미 돌고 있으면 새로 시작하지 않고 지금 상태를 돌려준다."""
    global _status
    with _lock:
        if _status.state == "running":
            return _status
        _status = RefreshStatus(
            state="running", stage="시작하는 중", started_at=dt.datetime.now(dt.UTC)
        )
    threading.Thread(target=_run, name="refresh", daemon=True).start()
    return _status


def _run() -> None:
    try:
        report = run_pipeline(on_stage=lambda s: _set(stage=s))
    except Exception as exc:  # noqa: BLE001 - 상태로 알리고 스레드는 조용히 끝낸다
        log.exception("새 공지 가져오기 실패")
        _set(state="failed", stage=None, finished_at=dt.datetime.now(dt.UTC), error=str(exc))
        return
    log.info("%s", report.render())
    _set(
        state="done",
        stage=None,
        finished_at=dt.datetime.now(dt.UTC),
        new=report.new,
        updated=report.updated,
        failed_sources=report.failed_sources,
    )
