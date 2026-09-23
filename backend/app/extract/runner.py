"""첨부 텍스트 추출 실행기.

extract_state 가 pending 인 첨부만 집어서 처리하고 결과를 기록한다.
지원하지 않는 확장자는 unsupported 로 표시해 다음 실행에서 다시 집지 않는다.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections import Counter

from sqlalchemy import select

from app.db import SessionLocal
from app.extract import hwp5, hwpx, pdf
from app.models import Attachment, ExtractState

log = logging.getLogger(__name__)

ENGINES = {
    "hwp": ("hwp5", hwp5.extract),
    "hwpx": ("hwpx", hwpx.extract),
    "pdf": ("pymupdf", pdf.extract),
}

# 본문이 이보다 짧으면 추출이 사실상 실패한 것으로 본다(스캔 이미지 PDF 등).
MIN_USEFUL_CHARS = 30


def run(limit: int | None = None, exts: list[str] | None = None) -> Counter[str]:
    stats: Counter[str] = Counter()

    with SessionLocal() as session:
        stmt = select(Attachment).where(
            Attachment.extract_state == ExtractState.pending,
            Attachment.storage_path.is_not(None),
        )
        if exts:
            stmt = stmt.where(Attachment.file_ext.in_(exts))
        if limit:
            stmt = stmt.limit(limit)

        for att in session.scalars(stmt).all():
            engine = ENGINES.get(att.file_ext or "")
            if engine is None:
                att.extract_state = ExtractState.unsupported
                stats[f"unsupported:{att.file_ext}"] += 1
                session.commit()
                continue

            name, fn = engine
            att.extract_engine = name
            try:
                text = fn(att.storage_path)
            except Exception as exc:  # noqa: BLE001 - 어떤 실패든 행에 남긴다
                att.extract_state = ExtractState.failed
                att.extract_error = f"{type(exc).__name__}: {exc}"[:500]
                stats[f"failed:{att.file_ext}"] += 1
                log.warning("추출 실패 %s: %s", att.filename, exc)
            else:
                att.extracted_text = text
                att.extracted_at = dt.datetime.now(dt.UTC)
                if len(text) < MIN_USEFUL_CHARS:
                    # 파싱은 됐지만 건질 게 없다. 스캔본일 가능성이 높다.
                    att.extract_state = ExtractState.unsupported
                    att.extract_error = f"추출 결과 {len(text)}자"
                    stats[f"empty:{att.file_ext}"] += 1
                else:
                    att.extract_state = ExtractState.ok
                    stats[f"ok:{att.file_ext}"] += 1
            session.commit()

    return stats
