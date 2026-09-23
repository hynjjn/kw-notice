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
  // 고정 여부로 섹션을 가르지 않는다. "전체 공지"가 고정을 빼고 보여 주고,
  // 고정만 보려면 사이드바에 전용 항목이 따로 있다.
  return (
    <>
      {notices.map((n) => (
        <Row
          key={n.id}
          notice={n}
          selected={n.id === selectedId}
          onSelect={() => onSelect(n)}
          onToggleStar={() => onToggleStar(n)}
        />
      ))}
    </>
  );
}
