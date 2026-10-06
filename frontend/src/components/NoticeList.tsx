import { useEffect, useRef } from "react";
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
      className="grid cursor-pointer grid-cols-[20px_1fr] items-start gap-2.5 px-4 py-2.5"
      style={{
        borderBottom: "1px solid var(--line-soft)",
        background: selected ? "var(--sel)" : undefined,
        boxShadow: selected ? "inset 3px 0 0 var(--accent)" : undefined,
      }}
      onClick={onSelect}
    >
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
          {/* 학교 사이트 목록 맨 위에 고정된 공지. 이모지는 CSS 색이 먹지 않아서
              예전처럼 모든 줄에 📌 를 두면 고정 여부를 구분할 수 없었다. */}
          {notice.is_pinned && (
            <span
              className="chip"
              // 고른 줄의 바탕이 accent-soft 라서 같은 색 칩은 묻힌다. 칩은 꽉 채운다.
              style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
              title="학교 사이트 목록 맨 위에 고정된 공지"
            >
              고정
            </span>
          )}
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
          {unread && (
            <span
              className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle"
              style={{ background: "var(--accent)" }}
              aria-label="안 읽음"
            />
          )}
          {notice.title}
        </div>
        <div
          className="mt-0.5 flex gap-2 text-[11.5px] tabular-nums"
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
  // 고정 여부로 섹션을 가르지 않는다. 고정 공지도 처음 본 날짜순으로 섞이고
  // "고정" 칩으로만 구분한다. 고정만 보려면 사이드바에 전용 항목이 있다.
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

/**
 * 목록 끝의 표시. 화면에 들어오기 조금 전(400px)에 다음 쪽을 부른다.
 * 관찰이 안 되는 환경을 위해 같은 자리를 버튼으로도 둔다.
 */
export function LoadMore({
  hasMore,
  loading,
  error,
  shown,
  total,
  onLoad,
}: {
  hasMore: boolean;
  loading: boolean;
  error: boolean;
  shown: number;
  total: number;
  onLoad: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    // 실패했으면 자동으로 다시 부르지 않는다. 화면에 머무는 동안 계속 재시도하게 된다.
    if (!el || !hasMore || loading || error) return;
    const observer = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && onLoad(),
      // 목록은 창이 아니라 <section> 안에서 스크롤된다. root 를 창으로 두면
      // section 이 잘라 낸 부분이라 rootMargin 이 먹지 않는다.
      { root: el.closest("section"), rootMargin: "400px 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, loading, error, onLoad]);

  if (shown === 0) return null;

  return (
    <div ref={ref} className="px-4 py-4 text-center text-[12px] tabular-nums" style={{ color: "var(--faint)" }}>
      {loading ? (
        "불러오는 중..."
      ) : error ? (
        <button type="button" onClick={onLoad} style={{ color: "var(--link)" }}>
          더 불러오지 못했습니다. 다시 시도
        </button>
      ) : hasMore ? (
        <button type="button" onClick={onLoad}>
          {shown} / {total}건 · 더 보기
        </button>
      ) : (
        `${total}건 모두 봤습니다`
      )}
    </div>
  );
}
