// backend/app/api/schemas.py 와 짝을 이룬다. 한쪽을 고치면 다른 쪽도 고쳐야 한다.

export interface Attachment {
  id: number;
  filename: string;
  url: string;
  file_ext: string | null;
  byte_size: number | null;
  extract_state: string;
  has_text: boolean;
  /** 서버에 받아 둔 파일이 있어 /attachments/{id}/file 로 미리 볼 수 있다. */
  has_file: boolean;
}

export interface Notice {
  id: number;
  source_key: string;
  source_name: string;
  external_id: string;
  url: string;
  title: string;
  category: string | null;
  author_dept: string | null;
  posted_at: string;
  modified_at_source: string | null;
  view_count: number;
  is_pinned: boolean;
  pinned_rank: number | null;
  has_attachment: boolean;
  attachment_count: number;
  deadline_at: string | null;
  ai_summary: string | null;
  content_revision: number;
  content_changed_at: string | null;
  is_read: boolean;
  is_starred: boolean;
}

export interface NoticeDetail extends Notice {
  /** 정제를 거친 원본 HTML. 서식과 이미지 위치가 여기에만 남아 있다. */
  body_html: string | null;
  body_text: string | null;
  inline_image_urls: string[] | null;
  attachments: Attachment[];
}

export interface NoticeList {
  items: Notice[];
  total: number;
  limit: number;
  offset: number;
}

export interface Count {
  key: string;
  label: string;
  count: number;
}

export interface Stats {
  total: number;
  unread: number;
  starred: number;
  pinned: number;
  deadline_soon: number;
  by_source: Count[];
  by_category: Count[];
}

export interface Digest {
  digest_date: string;
  summary_md: string;
  notice_ids: number[];
  model: string | null;
}

export interface NoticeQuery {
  source?: string;
  category?: string;
  pinned?: boolean;
  unread?: boolean;
  starred?: boolean;
  deadline_soon?: boolean;
  q?: string;
  sort?: "seen" | "posted" | "modified" | "views" | "deadline";
  limit?: number;
  offset?: number;
}

export interface ChatNoticeRef {
  id: number;
  title: string;
  deadline_at: string | null;
}

export interface ChatReply {
  reply: string;
  notices: ChatNoticeRef[];
  /** 이번 답에서 새로 저장하거나 지운 기억. */
  remembered: string[];
  forgotten: string[];
}

/** AI 채팅이 대화를 넘어 기억하는 사용자 정보. */
export interface Memory {
  id: number;
  content: string;
  created_at: string;
}

export interface RefreshStatus {
  state: "idle" | "running" | "done" | "failed";
  stage: string | null;
  started_at: string | null;
  finished_at: string | null;
  new: number;
  updated: number;
  failed_sources: string[];
  error: string | null;
  last_crawled_at: string | null;
}
