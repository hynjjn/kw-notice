import type { Notice } from "../api/types";

interface Props {
  notices: Notice[];
  selectedId: number | null;
  onSelect: (n: Notice) => void;
  onToggleStar: (n: Notice) => void;
}

function shortDate(iso: string) {
  const [, m, d] = iso.split("-");
  return `${m}-${d}`;
}

function Row({
  notice,
  selected,
  onSelect,
  onToggleStar,
}: {
  notice: Notice;
  selected: boolean;
  onSelect: () => void;
  onToggleStar: () => void;
}) {
  const unread = !notice.is_read;
  return (
    <div
      className="grid cursor-pointer grid-cols-[20px_20px_1fr] items-start gap-2.5 px-4 py-2.5"
      style={{
        borderBottom: "1px solid var(--line-soft)",
        background: selected ? "var(--sel)" : undefined,
        boxShadow: selected ? "inset 3px 0 0 var(--unread)" : undefined,
      }}
      onClick={onSelect}
    >
      <span
        className="text-[13px] leading-snug"
        style={{ color: notice.is_pinned ? "var(--accent)" : "var(--star-off)" }}
      >
        📌
      </span>
      <button
        className="text-[15px] leading-snug"
        style={{ color: notice.is_starred ? "var(--star)" : "var(--star-off)" }}
        onClick={(e) => {
          e.stopPropagation();
          onToggleStar();
        }}
        aria-label="별표"
      >
        {notice.is_starred ? "★" : "☆"}
      </button>
      <div className="min-w-0">
        <div
          className="mb-0.5 flex items-center gap-1.5 text-[11px]"
          style={{ color: unread ? "var(--body-text)" : "var(--muted)" }}
        >
          {notice.category && <span className="chip">{notice.category}</span>}
          {notice.source_key === "cs_dept" && <span className="chip">소프트웨어학부</span>}
          <span className="truncate">{notice.author_dept ?? notice.source_name}</span>
        </div>
        <div
          className="line-clamp-2 text-[13.5px]"
          style={{
            color: unread ? "var(--text)" : "var(--body-text)",
            fontWeight: unread ? 700 : 400,
          }}
        >
          {notice.title}
        </div>
        <div
          className="mt-0.5 flex gap-2 text-[11.5px]"
          style={{ color: "var(--faint)" }}
        >
          <span>{shortDate(notice.posted_at)}</span>
          {notice.attachment_count > 0 && <span>📎 {notice.attachment_count}</span>}
          {notice.deadline_at && <span>⏰ {shortDate(notice.deadline_at)}</span>}
          {notice.content_revision > 1 && (
            <span style={{ color: "var(--accent)" }}>변경됨</span>
          )}
        </div>
      </div>
    </div>
  );
}

export function NoticeList({ notices, selectedId, onSelect, onToggleStar }: Props) {
  const pinned = notices.filter((n) => n.is_pinned);
  const rest = notices.filter((n) => !n.is_pinned);

  const heading = (text: string) => (
    <div
      className="px-4 pt-2.5 pb-1.5 text-[11px] font-bold tracking-wide"
      style={{ color: "var(--faint)" }}
    >
      {text}
    </div>
  );

  const render = (n: Notice) => (
    <Row
      key={n.id}
      notice={n}
      selected={n.id === selectedId}
      onSelect={() => onSelect(n)}
      onToggleStar={() => onToggleStar(n)}
    />
  );

  return (
    <>
      {/* 고정 공지를 따로 접어 두는 게 이 서비스의 존재 이유다.
          학교 사이트는 68건 중 58건이 고정이라 새 공지가 파묻힌다. */}
      {rest.length > 0 && heading(`🆕 새 공지 ${rest.length}건`)}
      {rest.map(render)}
      {pinned.length > 0 && heading(`📌 고정 공지 ${pinned.length}건`)}
      {pinned.map(render)}
    </>
  );
}
