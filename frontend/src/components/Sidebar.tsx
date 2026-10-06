import type { Stats } from "../api/types";
import { filterToHash } from "../filterHash";

export type Filter = {
  source?: string;
  category?: string;
  unread?: boolean;
  starred?: boolean;
  pinned?: boolean;
  deadline_soon?: boolean;
};

interface Props {
  stats?: Stats;
  filter: Filter;
}

function same(a: Filter, b: Filter) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function Sidebar({ stats, filter }: Props) {
  // 버튼이 아니라 링크다. 고르면 주소의 # 만 바뀌고, 열어 둔 공지(?notice=)는 그대로 남는다.
  // 가운데 클릭으로 새 탭에 열 수도 있다.
  const item = (label: string, icon: string, next: Filter, count?: number) => (
    <a
      key={label}
      href={filterToHash(next)}
      className="nav-btn"
      data-active={same(filter, next)}
      aria-current={same(filter, next) ? "page" : undefined}
    >
      <span className="w-4.5 text-center">{icon}</span>
      <span className="truncate">{label}</span>
      {count !== undefined && (
        <span className="ml-auto text-xs font-semibold tabular-nums">{count}</span>
      )}
    </a>
  );

  const heading = (text: string) => (
    <div
      className="px-4 pt-3.5 pb-1.5 text-[11px] font-bold tracking-wide"
      style={{ color: "var(--faint)" }}
    >
      {text}
    </div>
  );

  return (
    <nav className="overflow-y-auto px-2 py-3">
      {/* 고정 공지도 섞어 보여 준다. 학교는 새 공지 대부분을 고정으로 올린다.
          오래된 고정 공지는 처음 본 날짜순 정렬에서 저절로 아래로 내려간다. */}
      {item("전체 공지", "📥", {}, stats?.total)}
      {item("안 읽음", "✳️", { unread: true }, stats?.unread)}
      {item("별표", "⭐", { starred: true }, stats?.starred)}
      {item("학교 고정 공지", "📌", { pinned: true }, stats?.pinned)}
      {item("마감 임박", "⏰", { deadline_soon: true }, stats?.deadline_soon)}

      {heading("출처")}
      {stats?.by_source.map((s) =>
        item(s.label, s.key === "cs_dept" ? "💻" : "🏫", { source: s.key }, s.count),
      )}

      {heading("분류")}
      {stats?.by_category.map((c) => item(c.label, "●", { category: c.key }, c.count))}
    </nav>
  );
}
