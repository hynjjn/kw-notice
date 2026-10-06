import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useChat } from "./chat/chat";
import { ChatFab } from "./chat/ChatFab";
import { DigestCard } from "./components/DigestCard";
import { LoadMore, NoticeList } from "./components/NoticeList";
import { ReadingPane } from "./components/ReadingPane";
import { RefreshButton } from "./components/RefreshButton";
import { Sidebar } from "./components/Sidebar";
import { hashToFilter } from "./filterHash";
import { ThemeToggle } from "./components/ThemeToggle";
import { useDigest, useNotice, useNotices, useSetRead, useSetStar, useStats } from "./hooks";
import type { Notice } from "./api/types";

const today = new Date().toISOString().slice(0, 10);

export default function App() {
  // 사이드바에서 고른 목록은 주소의 # 에 있다(#unread, #category/일반 등).
  // # 이 없으면 "전체 공지"다.
  const { hash } = useLocation();
  const filter = useMemo(() => hashToFilter(hash), [hash]);
  const [search, setSearch] = useState("");
  // 고른 공지는 주소(?notice=ID)에 둔다. AI 채팅의 공지 링크가 이 주소로 와서
  // 공지를 연다. 새로고침이나 링크 공유에도 같은 공지가 열린다.
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const selectedId = Number(params.get("notice")) || null;

  const query = useMemo(
    // 우리가 처음 본 순서로 줄 세운다. 오래된 공지가 수정돼서 다시 올라온
    // 경우도 맨 위에 잡힌다.
    () => ({ ...filter, q: search || undefined, sort: "seen" as const }),
    [filter, search],
  );

  const notices = useNotices(query);
  // 쪽을 이어 붙인다. 넘겨 보는 사이 새 공지가 들어오면 offset 이 밀려
  // 같은 공지가 두 쪽에 걸칠 수 있어서 id 로 한 번 거른다.
  const items = useMemo(() => {
    const seen = new Set<number>();
    return (notices.data?.pages ?? [])
      .flatMap((p) => p.items)
      .filter((n) => !seen.has(n.id) && seen.add(n.id));
  }, [notices.data]);
  const total = notices.data?.pages[0]?.total ?? 0;
  const stats = useStats();
  const detail = useNotice(selectedId);
  const digest = useDigest(today);
  const setRead = useSetRead();
  const setStar = useSetStar();

  // 열어 둔 공지를 채팅에 알린다. 채팅 페이지로 가면 이 화면이 사라지므로 비운다.
  const { setCurrentNotice } = useChat();
  const openId = detail.data?.id;
  const openTitle = detail.data?.title;
  useEffect(() => {
    setCurrentNotice(openId != null && openTitle ? { id: openId, title: openTitle } : null);
  }, [openId, openTitle, setCurrentNotice]);
  useEffect(() => () => setCurrentNotice(null), [setCurrentNotice]);

  function select(n: Notice) {
    // setSearchParams 는 # 을 떨어뜨린다. 고른 목록이 풀리지 않게 hash 를 같이 넘긴다.
    navigate({ search: `?notice=${n.id}`, hash });
    if (!n.is_read) setRead.mutate({ id: n.id, value: true });
  }

  return (
    <div className="flex h-full flex-col">
      <header
        className="sticky top-0 z-20 flex h-15 items-center gap-4 px-4"
        style={{ background: "var(--surface)", borderBottom: "1px solid var(--line)" }}
      >
        <div className="flex items-center gap-2.5 text-lg font-bold tracking-tight">
          <span
            className="grid h-5.5 w-5.5 place-items-center rounded-lg text-xs font-extrabold"
            style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
          >
            KW
          </span>
          Notice
        </div>
        <div
          className="flex h-10 max-w-2xl flex-1 items-center gap-2.5 rounded-full px-4"
          style={{ background: "var(--search-bg)", color: "var(--muted)" }}
        >
          🔍
          <input
            className="flex-1 bg-transparent outline-none"
            style={{ color: "var(--text)" }}
            placeholder="공지 검색: 첨부파일 내용까지 찾습니다"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button onClick={() => setSearch("")} aria-label="검색어 지우기">
              ✕
            </button>
          )}
        </div>
        <div className="ml-auto flex items-center gap-3">
          <RefreshButton />
          <ThemeToggle />
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[212px_minmax(340px,440px)_1fr]">
        <Sidebar stats={stats.data} filter={filter} />

        <section
          className="overflow-y-auto"
          style={{
            background: "var(--surface)",
            borderLeft: "1px solid var(--line)",
            borderRight: "1px solid var(--line)",
          }}
        >
          {!search && <DigestCard digest={digest.data} date={today} />}

          {notices.isLoading && (
            <div className="p-4" style={{ color: "var(--muted)" }}>
              불러오는 중...
            </div>
          )}
          {notices.isError && (
            <div className="p-4" style={{ color: "var(--accent)" }}>
              API에 연결하지 못했습니다. uvicorn이 8000 포트에 떠 있는지 확인하세요.
            </div>
          )}
          {notices.data && (
            <>
              {search && (
                <div className="px-4 pt-3 text-[12px]" style={{ color: "var(--muted)" }}>
                  "{search}" 검색 결과 {total}건
                </div>
              )}
              <NoticeList
                notices={items}
                selectedId={selectedId}
                onSelect={select}
                onToggleStar={(n) => setStar.mutate({ id: n.id, value: !n.is_starred })}
              />
              <LoadMore
                hasMore={!!notices.hasNextPage}
                loading={notices.isFetchingNextPage}
                error={notices.isFetchNextPageError}
                shown={items.length}
                total={total}
                onLoad={() => notices.fetchNextPage()}
              />
            </>
          )}
        </section>

        <ReadingPane notice={detail.data} loading={detail.isLoading} />
      </div>

      <ChatFab />
    </div>
  );
}
