"""API 응답 DTO.

ORM 모델을 그대로 내보내지 않는다. body_html 처럼 프론트에 필요 없거나
무거운 필드가 섞여 나가는 걸 막기 위해서다.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    url: str
    file_ext: str | None
    byte_size: int | None
    extract_state: str
    has_text: bool


class NoticeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_key: str
    source_name: str
    external_id: str
    url: str
    title: str
    category: str | None
    author_dept: str | None
    posted_at: dt.date
    modified_at_source: dt.date | None
    view_count: int
    is_pinned: bool
    pinned_rank: int | None
    has_attachment: bool
    attachment_count: int
    deadline_at: dt.date | None
    ai_summary: str | None
    content_revision: int
    content_changed_at: dt.datetime | None
    is_read: bool
    is_starred: bool


class NoticeListItem(NoticeBase):
    pass


class NoticeDetail(NoticeBase):
    body_text: str | None
    inline_image_urls: list[str] | None
    attachments: list[AttachmentOut]


class NoticeListResponse(BaseModel):
    items: list[NoticeListItem]
    total: int
    limit: int
    offset: int


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    last_crawled_at: dt.datetime | None
    notice_count: int


class CountOut(BaseModel):
    key: str
    label: str
    count: int


class StatsOut(BaseModel):
    total: int
    unread: int
    starred: int
    pinned: int
    deadline_soon: int
    by_source: list[CountOut]
    by_category: list[CountOut]


class DigestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    digest_date: dt.date
    summary_md: str
    notice_ids: list[int]
    model: str | None


class StateOut(BaseModel):
    notice_id: int
    is_read: bool
    is_starred: bool
