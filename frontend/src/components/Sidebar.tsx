import type { Stats } from "../api/types";

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
  onChange: (f: Filter) => void;
}

function same(a: Filter, b: Filter) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function Sidebar({ stats, filter, onChange }: Props) {
  const item = (label: string, icon: string, next: Filter, count?: number) => (
    <button
      key={label}
      className="nav-btn"
      data-active={same(filter, next)}
      onClick={() => onChange(next)}
    >
      <span className="w-4.5 text-center">{icon}</span>
      <span className="truncate">{label}</span>
      {count !== undefined && (
        <span className="ml-auto text-xs font-semibold">{count}</span>
      )}
    </button>
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
      {item("전체 공지", "📥", {}, stats?.total)}
      {item("안 읽음", "✳️", { unread: true }, stats?.unread)}
      {item("별표", "⭐", { starred: true }, stats?.starred)}
      {item("고정 공지", "📌", { pinned: true }, stats?.pinned)}
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
