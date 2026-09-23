"""KW Notice 스키마.

설계 결정 요약은 README.md 의 "스키마 결정" 절 참고.
"""

from __future__ import annotations

import datetime as dt
import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# 임베딩 모델을 바꾸면 이 값도 바뀐다. 바꿀 때는 컬럼 재생성이 필요하다.
EMBEDDING_DIM = 1024


class Base(DeclarativeBase):
    pass


def _ts() -> Mapped[dt.datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class CrawlState(str, enum.Enum):
    listed = "listed"      # 목록에서 발견만 됨
    fetched = "fetched"    # 상세 HTML 받음
    parsed = "parsed"      # 본문, 첨부 목록 파싱 완료
    failed = "failed"


class ExtractState(str, enum.Enum):
    pending = "pending"
    ok = "ok"
    unsupported = "unsupported"   # 확장자는 알지만 파서가 못 다루는 경우
    failed = "failed"


class RunStatus(str, enum.Enum):
    running = "running"
    ok = "ok"
    failed = "failed"


crawl_state_enum = ENUM(CrawlState, name="crawl_state", create_type=True)
extract_state_enum = ENUM(ExtractState, name="extract_state", create_type=True)
run_status_enum = ENUM(RunStatus, name="run_status", create_type=True)


class Source(Base):
    """크롤링 대상 게시판.

    학부 게시판이 늘어나도 코드 수정 없이 행 추가로 끝나게 테이블로 둔다.
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)      # kw_main, cs_dept
    name: Mapped[str] = mapped_column(String(64))
    list_url: Mapped[str] = mapped_column(Text)
    parser: Mapped[str] = mapped_column(String(32))                # 파서 구현 이름
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawled_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    notices: Mapped[list[Notice]] = relationship(back_populates="source")


class Notice(Base):
    __tablename__ = "notices"
    __table_args__ = (
        # 중복 판정 키. 목록에 보이는 번호가 아니라 상세 URL 의 고유 ID 를 쓴다.
        # 대학 공지는 DUID, 소프트웨어학부는 no 파라미터. 학부 게시판은 표시 번호(77)와
        # URL 의 no(3417)가 달라서, 표시 번호를 키로 쓰면 글이 지워질 때 어긋난다.
        UniqueConstraint("source_id", "external_id", name="uq_notice_source_external"),
        Index("ix_notice_posted_at", "posted_at"),
        Index("ix_notice_pinned", "is_pinned", "pinned_rank"),
        Index("ix_notice_tsv", "tsv", postgresql_using="gin"),
        Index("ix_notice_deadline", "deadline_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(Text)

    # ── 목록에서 얻는 값 ─────────────────────────────
    category: Mapped[str | None] = mapped_column(String(32))   # 학생, 일반, 등록/장학. 학부 게시판은 null
    title: Mapped[str] = mapped_column(Text)
    author_dept: Mapped[str | None] = mapped_column(String(64))
    posted_at: Mapped[dt.date] = mapped_column(Date)
    modified_at_source: Mapped[dt.date | None] = mapped_column(Date)  # 대학 공지의 수정일
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    has_attachment: Mapped[bool] = mapped_column(Boolean, default=False)

    # 고정 공지는 현재 상태만 들고 간다. 이력은 남기지 않는다.
    # 고정 여부는 "목록에서의 행 순서가 날짜 정렬 순서와 어긋나는가"로 판정한다.
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned_rank: Mapped[int | None] = mapped_column(Integer)

    # ── 상세에서 얻는 값 ─────────────────────────────
    body_html: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    # 본문이 포스터 이미지 한 장뿐인 공지가 적지 않다. 이 경우 body_text 가 비고
    # 요약할 재료가 없으므로, 4단계에서 vision 으로 읽을 이미지 URL 을 들고 있는다.
    inline_image_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # 본문 변경 감지. normalize(body_text) 의 sha256.
    # 값이 달라지면 content_revision 을 올리고 요약을 다시 만든다.
    content_hash: Mapped[str | None] = mapped_column(String(64))
    content_revision: Mapped[int] = mapped_column(Integer, default=1)
    content_changed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    crawl_state: Mapped[CrawlState] = mapped_column(crawl_state_enum, default=CrawlState.listed)
    crawl_error: Mapped[str | None] = mapped_column(Text)

    # ── AI 산출물 ────────────────────────────────────
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_summary_model: Mapped[str | None] = mapped_column(String(64))
    ai_summarized_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # 요약 단계에서 뽑는 마감일. "마감 임박한 것만" 필터가 이 컬럼을 쓴다.
    deadline_at: Mapped[dt.date | None] = mapped_column(Date)

    # ── 수집 메타 ────────────────────────────────────
    first_seen_at: Mapped[dt.datetime] = _ts()
    last_seen_at: Mapped[dt.datetime] = _ts()

    # 한국어 형태소 분석 없이 simple 구성으로 시작한다.
    # 검색 품질이 아쉬워지면 pg_bigm 을 얹고 이 컬럼은 그대로 둔다.
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(body_text,''))",
            persisted=True,
        ),
    )

    source: Mapped[Source] = relationship(back_populates="notices")
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="notice", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        # 첨부의 신원은 다운로드 URL 이다. sha256 은 실제로 받은 뒤에야 알 수 있어서
        # 식별 키로 쓸 수 없다(목록만 수집하는 실행에서는 비어 있다).
        UniqueConstraint("notice_id", "url", name="uq_attachment_notice_url"),
        Index("ix_attachment_extract_state", "extract_state"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"))

    filename: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    file_ext: Mapped[str | None] = mapped_column(String(16))   # hwp, hwpx, pdf, zip
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    storage_path: Mapped[str | None] = mapped_column(Text)

    extract_state: Mapped[ExtractState] = mapped_column(
        extract_state_enum, default=ExtractState.pending
    )
    extract_engine: Mapped[str | None] = mapped_column(String(32))  # rhwp, hwp5, pymupdf
    extracted_text: Mapped[str | None] = mapped_column(Text)
    extracted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    extract_error: Mapped[str | None] = mapped_column(Text)

    notice: Mapped[Notice] = relationship(back_populates="attachments")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = _ts()


class UserNoticeState(Base):
    """읽음, 별표 같은 사용자별 상태.

    notices 본문에 섞지 않는다. 나중에 사용자가 늘어나도 구조가 안 바뀐다.
    """

    __tablename__ = "user_notice_state"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    notice_id: Mapped[int] = mapped_column(
        ForeignKey("notices.id", ondelete="CASCADE"), primary_key=True
    )

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    starred_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)


class DailyDigest(Base):
    """하루치 요약. user_id 가 null 이면 전체 공용 요약."""

    __tablename__ = "daily_digests"
    __table_args__ = (
        UniqueConstraint("user_id", "digest_date", name="uq_digest_user_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    digest_date: Mapped[dt.date] = mapped_column(Date)
    summary_md: Mapped[str] = mapped_column(Text)
    notice_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    model: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = _ts()


class NoticeChunk(Base):
    """RAG 용 청크. 본문 청크는 attachment_id 가 null, 첨부 청크는 채워진다."""

    __tablename__ = "notice_chunks"
    __table_args__ = (
        UniqueConstraint(
            "notice_id", "attachment_id", "chunk_index", name="uq_chunk_position"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"))
    attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    # 청크는 본문 개정마다 다시 만든다. 어느 개정의 청크인지 남겨 둔다.
    content_revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = _ts()


# 벡터 인덱스는 행이 어느 정도 쌓인 뒤에 만드는 편이 낫다.
# 초기에는 순차 스캔이 더 빠르고, 비어 있는 테이블에 만든 ivfflat 은 품질이 나쁘다.
Index(
    "ix_chunk_embedding",
    NoticeChunk.embedding,
    postgresql_using="hnsw",
    postgresql_with={"m": 16, "ef_construction": 64},
    postgresql_ops={"embedding": "vector_cosine_ops"},
)


class CrawlRun(Base):
    """크롤 실행 로그. 조용한 실패를 잡기 위한 테이블이다."""

    __tablename__ = "crawl_runs"
    __table_args__ = (
        CheckConstraint("found_count >= 0", name="ck_run_found_nonneg"),
        Index("ix_run_started", "started_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    started_at: Mapped[dt.datetime] = _ts()
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RunStatus] = mapped_column(run_status_enum, default=RunStatus.running)
    found_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
