import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useChat } from "./chat";
import { ChatPanel } from "./ChatPanel";

/** 오른쪽 아래 버튼과, 누르면 뜨는 작은 채팅 창. */
export function ChatFab() {
  const {
    floatingOpen,
    setFloatingOpen,
    messages,
    reset,
    currentNotice,
    attachNotice,
    setAttachNotice,
  } = useChat();

  useEffect(() => {
    if (!floatingOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFloatingOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [floatingOpen, setFloatingOpen]);

  return (
    <>
      {floatingOpen && (
        <div
          role="dialog"
          aria-label="AI 채팅"
          className="fixed right-6 bottom-24 z-40 flex h-[min(600px,calc(100vh-8rem))] w-[min(400px,calc(100vw-2rem))] flex-col overflow-hidden rounded-3xl shadow-2xl"
          style={{ background: "var(--surface)", border: "1px solid var(--line)" }}
        >
          <div
            className="flex items-center gap-2 px-4 py-3"
            style={{ borderBottom: "1px solid var(--line)" }}
          >
            <span className="font-bold" style={{ color: "var(--text)" }}>
              ✨ AI 채팅
            </span>
            <div className="ml-auto flex items-center gap-1 text-[12.5px]">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={reset}
                  className="rounded-lg px-2 py-1"
                  style={{ color: "var(--muted)" }}
                >
                  새 대화
                </button>
              )}
              <Link
                to="/chat"
                onClick={() => setFloatingOpen(false)}
                className="rounded-lg px-2 py-1"
                style={{ color: "var(--muted)" }}
                aria-label="전체 화면으로 열기"
                title="전체 화면으로 열기"
              >
                ⤢
              </Link>
              <button
                type="button"
                onClick={() => setFloatingOpen(false)}
                className="rounded-lg px-2 py-1"
                style={{ color: "var(--muted)" }}
                aria-label="닫기"
              >
                ✕
              </button>
            </div>
          </div>
          {currentNotice &&
            (attachNotice ? (
              <div
                className="flex items-center gap-2 px-4 py-2 text-[12px]"
                style={{
                  background: "var(--accent-soft)",
                  borderBottom: "1px solid var(--line)",
                  borderLeft: "3px solid var(--accent)",
                }}
              >
                <span className="shrink-0 font-bold" style={{ color: "var(--accent)" }}>
                  👀 보고 있는 공지
                </span>
                <span className="min-w-0 flex-1 truncate" style={{ color: "var(--text)" }} title={currentNotice.title}>
                  {currentNotice.title}
                </span>
                <button
                  type="button"
                  onClick={() => setAttachNotice(false)}
                  className="shrink-0 px-1"
                  style={{ color: "var(--muted)" }}
                  aria-label="이 공지를 질문에서 빼기"
                  title="이 공지를 질문에서 빼기"
                >
                  ✕
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setAttachNotice(true)}
                className="truncate px-4 py-2 text-left text-[12px]"
                style={{ borderBottom: "1px solid var(--line)", color: "var(--muted)" }}
                title={currentNotice.title}
              >
                + 보고 있는 공지 기준으로 묻기: {currentNotice.title}
              </button>
            ))}
          <ChatPanel compact />
        </div>
      )}

      <button
        type="button"
        onClick={() => setFloatingOpen(!floatingOpen)}
        aria-label={floatingOpen ? "AI 채팅 닫기" : "AI 채팅 열기"}
        aria-expanded={floatingOpen}
        className="fixed right-6 bottom-6 z-40 grid h-14 w-14 place-items-center rounded-full text-2xl shadow-lg transition-transform hover:scale-105"
        style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
      >
        {floatingOpen ? "✕" : "✨"}
      </button>
    </>
  );
}
