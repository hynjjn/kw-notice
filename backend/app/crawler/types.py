from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field


@dataclass
class ListItem:
    """목록 한 줄에서 얻는 값."""

    external_id: str
    url: str
    title: str
    posted_at: dt.date
    category: str | None = None
    author_dept: str | None = None
    modified_at_source: dt.date | None = None
    view_count: int = 0
    has_attachment: bool = False
    is_pinned: bool = False
    pinned_rank: int | None = None


@dataclass
class AttachmentRef:
    filename: str
    url: str


@dataclass
class Detail:
    """상세 페이지에서 얻는 값."""

    body_html: str
    body_text: str
    attachments: list[AttachmentRef] = field(default_factory=list)
    inline_image_urls: list[str] = field(default_factory=list)
