"""크롤 실행 오케스트레이션.

목록 수집 → 상세 진입 → 첨부 다운로드 → upsert 까지 한 번에 돈다.
첨부 텍스트 추출은 여기서 하지 않는다. extract_state 를 pending 으로 남겨 두면
3단계 파서가 그 행만 집어 간다.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.crawler import cs_dept, filetype, kw_main
from app.crawler.http import Blocked, Fetch, Fetcher, make_client
from app.crawler.text import content_hash
from app.crawler.types import Detail, ListItem
from app.db import SessionLocal
from app.models import Attachment, CrawlRun, CrawlState, ExtractState, Notice, RunStatus, Source

log = logging.getLogger(__name__)

PARSERS = {"kw_main": kw_main, "cs_dept": cs_dept}
_UNSAFE = re.compile(r"[^\w.\-가-힣() ]+")


@dataclass
class RunStats:
    found: int = 0
    new: int = 0
    updated: int = 0
    detail_fetched: int = 0
    attachments: int = 0
    bad_files: int = 0
    failed: int = 0
    blocked: bool = False


def _safe_name(name: str) -> str:
    return _UNSAFE.sub("_", name).strip()[:180] or "attachment"


def collect_list(fetcher: Fetcher, parser, pages: int) -> list[ListItem]:
    """여러 페이지를 훑고 external_id 로 중복을 제거한다.

    고정 공지는 모든 페이지에 반복해서 나오므로 중복 제거가 필수다.
    먼저 만난 쪽을 남겨야 1페이지 기준 pinned_rank 가 유지된다.
    """
    seen: dict[str, ListItem] = {}
    for page in range(1, pages + 1):
        res = fetcher.get(parser.page_url(page))
        for item in parser.parse_list(res.text):
            seen.setdefault(item.external_id, item)
    return list(seen.values())


def _apply_list_fields(notice: Notice, item: ListItem) -> None:
    notice.title = item.title
    notice.category = item.category
    notice.author_dept = item.author_dept
    notice.posted_at = item.posted_at
    notice.modified_at_source = item.modified_at_source
    notice.view_count = item.view_count
    notice.has_attachment = item.has_attachment
    notice.is_pinned = item.is_pinned
    notice.pinned_rank = item.pinned_rank
    notice.last_seen_at = dt.datetime.now(dt.UTC)


def _needs_detail(notice: Notice, item: ListItem, was_new: bool) -> bool:
    if was_new or notice.crawl_state != CrawlState.parsed:
        return True
    # 수정일이 올라갔으면 본문이 바뀌었을 수 있다.
    return (
        item.modified_at_source is not None
        and notice.modified_at_source is not None
        and item.modified_at_source > notice.modified_at_source
    )


def _apply_detail(notice: Notice, detail: Detail) -> bool:
    """본문을 반영하고, 내용이 실제로 바뀌었는지 돌려준다."""
    new_hash = content_hash(detail.body_text)
    changed = notice.content_hash is not None and new_hash != notice.content_hash

    notice.body_html = detail.body_html
    notice.body_text = detail.body_text
    notice.inline_image_urls = detail.inline_image_urls or None
    notice.content_hash = new_hash
    notice.crawl_state = CrawlState.parsed
    notice.crawl_error = None

    if changed:
        notice.content_revision += 1
        notice.content_changed_at = dt.datetime.now(dt.UTC)
    return changed


def _store_attachments(
    session: Session, fetcher: Fetcher, notice: Notice, detail: Detail, download: bool
) -> tuple[int, int]:
    """첨부 행을 만들고 필요하면 파일을 받는다. (추가, 불량) 을 돌려준다."""
    known = {a.url for a in notice.attachments}
    added = bad = 0

    for ref in detail.attachments:
        if ref.url in known:
            continue
        known.add(ref.url)

        ext = ref.filename.rsplit(".", 1)[-1].lower() if "." in ref.filename else None
        att = Attachment(
            notice=notice,
            filename=ref.filename,
            url=ref.url,
            file_ext=ext[:16] if ext else None,
        )
        added += 1

        if download:
            try:
                payload = fetcher.get(ref.url).content
            except Fetch as exc:
                att.extract_state = ExtractState.failed
                att.extract_error = str(exc)[:500]
                bad += 1
                log.warning("첨부 다운로드 실패: %s", ref.filename)
                payload = None

            if payload is not None:
                # 확장자만 믿지 않는다. 내용이 그 포맷인지 본다.
                why = filetype.problem(att.file_ext, payload)
                if why:
                    att.extract_state = ExtractState.failed
                    att.extract_error = why
                    bad += 1
                    log.warning("첨부 내용 이상: %s (%s)", ref.filename, why)
                else:
                    target = (
                        settings.attachment_dir
                        / notice.source.key
                        / notice.external_id
                        / _safe_name(ref.filename)
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(payload)
                    att.storage_path = str(target)
                    att.sha256 = hashlib.sha256(payload).hexdigest()
                    att.byte_size = len(payload)

        session.add(att)

    return added, bad


def run_source(
    source_key: str,
    *,
    pages: int = 1,
    limit: int | None = None,
    fetch_detail: bool = True,
    download: bool = True,
) -> RunStats:
    parser = PARSERS[source_key]
    stats = RunStats()

    with SessionLocal() as session, make_client() as client:
        source = session.scalar(select(Source).where(Source.key == source_key))
        if source is None:
            raise ValueError(f"source 가 없다: {source_key}. python -m app.init_db 먼저.")

        fetcher = Fetcher(client=client, delay=parser.REQUEST_DELAY)
        run = CrawlRun(source_id=source.id)
        session.add(run)
        session.commit()

        try:
            items = collect_list(fetcher, parser, pages)
            stats.found = len(items)
            if limit:
                items = items[:limit]

            for item in items:
                notice = session.scalar(
                    select(Notice).where(
                        Notice.source_id == source.id,
                        Notice.external_id == item.external_id,
                    )
                )
                was_new = notice is None
                if was_new:
                    notice = Notice(
                        source_id=source.id, external_id=item.external_id, url=item.url
                    )
                    session.add(notice)
                    stats.new += 1

                want_detail = _needs_detail(notice, item, was_new)
                _apply_list_fields(notice, item)
                session.flush()

                if fetch_detail and want_detail:
                    try:
                        detail = parser.parse_detail(
                            fetcher.get(item.url).text, page_url_=item.url
                        )
                    except (Fetch, ValueError) as exc:
                        notice.crawl_state = CrawlState.failed
                        notice.crawl_error = str(exc)[:500]
                        stats.failed += 1
                        log.warning("상세 실패 %s: %s", item.external_id, exc)
                    else:
                        if _apply_detail(notice, detail) and not was_new:
                            stats.updated += 1
                        stats.detail_fetched += 1
                        added, bad = _store_attachments(
                            session, fetcher, notice, detail, download
                        )
                        stats.attachments += added
                        stats.bad_files += bad

                session.commit()

            source.last_crawled_at = dt.datetime.now(dt.UTC)
            run.status = RunStatus.ok

        except Blocked as exc:
            # 계속 두드리면 차단만 길어진다. 받은 데까지 남기고 접는다.
            stats.blocked = True
            run.status = RunStatus.failed
            run.error = f"차단됨: {exc}"[:2000]
            log.error("%s 가 우리를 막았다. 이번 실행을 중단한다: %s", source_key, exc)
        except Exception as exc:
            run.status = RunStatus.failed
            run.error = str(exc)[:2000]
            raise
        finally:
            run.finished_at = dt.datetime.now(dt.UTC)
            run.found_count = stats.found
            run.new_count = stats.new
            run.updated_count = stats.updated
            session.commit()

    return stats
