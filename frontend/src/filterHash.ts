import type { Filter } from "./components/Sidebar";

// 사이드바에서 고른 목록을 주소의 # 뒤에 둔다(Gmail 의 #inbox, #label/... 처럼).
// 새로고침, 뒤로 가기, 새 탭 열기에도 같은 목록이 나온다.
// 고른 공지는 ?notice=ID 에 따로 둔다. AI 채팅의 링크가 그 형식이다.
const SIMPLE: Record<string, Filter> = {
  all: {},
  unread: { unread: true },
  starred: { starred: true },
  pinned: { pinned: true },
  deadline: { deadline_soon: true },
};

export function filterToHash(f: Filter): string {
  if (f.source) return `#source/${encodeURIComponent(f.source)}`;
  // 분류에는 "등록/장학"처럼 / 가 들어간다. 인코딩해서 경로 구분자와 겹치지 않게 한다.
  if (f.category) return `#category/${encodeURIComponent(f.category)}`;
  const key = Object.keys(SIMPLE).find((k) => JSON.stringify(SIMPLE[k]) === JSON.stringify(f));
  return `#${key ?? "all"}`;
}

/** 모르는 값이면 전체 공지로 돌아간다. */
export function hashToFilter(hash: string): Filter {
  const raw = hash.replace(/^#/, "");
  const slash = raw.indexOf("/");
  if (slash > 0) {
    const kind = raw.slice(0, slash);
    let value: string;
    try {
      value = decodeURIComponent(raw.slice(slash + 1));
    } catch {
      return {};
    }
    if (!value) return {};
    if (kind === "source") return { source: value };
    if (kind === "category") return { category: value };
    return {};
  }
  return SIMPLE[raw] ?? {};
}
