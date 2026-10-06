import { Link } from "react-router-dom";
import { useChat } from "../chat/chat";
import { ChatPanel } from "../chat/ChatPanel";
import { MemoryToggle } from "../chat/MemoryPanel";
import { ThemeToggle } from "../components/ThemeToggle";

/** 긴 대화를 위한 전용 페이지. 떠 있는 창과 대화를 공유한다. */
export function ChatPage() {
  const { messages, reset } = useChat();

  return (
    <div className="flex h-full flex-col">
      <header
        className="sticky top-0 z-20 flex h-15 items-center gap-4 px-4"
        style={{ background: "var(--surface)", borderBottom: "1px solid var(--line)" }}
      >
        <Link to="/" className="flex items-center gap-2.5 text-lg font-bold tracking-tight">
          <span
            className="grid h-5.5 w-5.5 place-items-center rounded-lg text-xs font-extrabold"
            style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
          >
            KW
          </span>
          Notice
        </Link>
        <span className="text-[13px]" style={{ color: "var(--muted)" }}>
          / AI 채팅
        </span>
        <div className="ml-auto flex items-center gap-3 text-[13px]">
          <MemoryToggle />
          {messages.length > 0 && (
            <button type="button" onClick={reset} style={{ color: "var(--muted)" }}>
              새 대화
            </button>
          )}
          <Link to="/" style={{ color: "var(--link)" }}>
            ← 공지로
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col">
        <ChatPanel />
      </main>
    </div>
  );
}
