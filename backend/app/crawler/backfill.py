"""아직 내려받지 않은 첨부를 채워 넣는다.

목록만 수집한 실행(--no-download) 뒤에, 파서 검증에 필요한 확장자만
골라서 받을 때 쓴다.
"""

from __future__ import annotations

import argparse
import hashlib
import logging

from sqlalchemy import select

from app.config import settings
from app.crawler import filetype
from app.crawler.http import Blocked, Fetch, Fetcher, make_client
from app.crawler.runner import _safe_name
from app.db import SessionLocal
from app.models import Attachment, ExtractState

log = logging.getLogger(__name__)


def backfill(exts: list[str] | None, limit: int | None, delay: float) -> tuple[int, int]:
    done = failed = 0
    with SessionLocal() as session, make_client() as client:
        fetcher = Fetcher(client=client, delay=delay)
        stmt = select(Attachment).where(Attachment.storage_path.is_(None))
        if exts:
            stmt = stmt.where(Attachment.file_ext.in_(exts))
        if limit:
            stmt = stmt.limit(limit)

        for att in session.scalars(stmt).all():
            try:
                payload = fetcher.get(att.url).content
            except Blocked:
                log.error("차단됨. 남은 첨부는 다음 실행으로 미룬다")
                break
            except Fetch as exc:
                att.extract_state = ExtractState.failed
                att.extract_error = str(exc)[:500]
                session.commit()
                failed += 1
                continue

            why = filetype.problem(att.file_ext, payload)
            if why:
                att.extract_state = ExtractState.failed
                att.extract_error = why
                session.commit()
                log.warning("내용 이상: %s (%s)", att.filename, why)
                failed += 1
                continue

            target = (
                settings.attachment_dir
                / att.notice.source.key
                / att.notice.external_id
                / _safe_name(att.filename)
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)

            att.storage_path = str(target)
            att.sha256 = hashlib.sha256(payload).hexdigest()
            att.byte_size = len(payload)
            session.commit()
            done += 1

    return done, failed


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m app.crawler.backfill")
    p.add_argument("--ext", nargs="*", help="받을 확장자 (예: hwp hwpx)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--delay", type=float, default=1.0, help="요청 간 간격(초)")
    args = p.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    done, failed = backfill(args.ext, args.limit, args.delay)
    print(f"내려받음 {done} / 실패 {failed}")


if __name__ == "__main__":
    main()
