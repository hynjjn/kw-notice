import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Markdown } from "../components/Markdown";
import { useChat } from "./chat";

const SUGGESTIONS = [
  "이번 주에 마감되는 장학금 알려줘",
  "외국인 유학생 대상 공지만 모아줘",
  "통장사본 내야 하는 공지가 뭐야?",
];

/** 대화 목록과 입력창. 떠 있는 창과 전용 페이지가 같이 쓴다. */
export function ChatPanel({ compact = false }: { compact?: boolean }) {
  const { messages, pending, send } = useChat();
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, pending]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!draft.trim() || pending) return;
    send(draft);
    setDraft("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // 한글 조합 중의 Enter 는 글자를 확정하는 키다. 보내면 마지막 글자가 두 번 간다.
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className={`min-h-0 flex-1 overflow-y-auto ${compact ? "px-4 py-3" : "px-6 py-6"}`}>
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="text-3xl">✨</div>
            <div>
              <div className="font-bold" style={{ color: "var(--text)" }}>
                공지에 대해 물어보세요
              </div>
              <div className="mt-1 text-[12.5px]" style={{ color: "var(--muted)" }}>
                본문과 첨부파일 내용까지 찾아서 답합니다
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="rounded-xl px-3 py-2 text-[12.5px]"
                  style={{ border: "1px solid var(--line)", color: "var(--body-text)" }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((m) =>
              m.role === "user" ? (
                <div
                  key={m.id}
                  className="max-w-[85%] self-end rounded-2xl rounded-br-md px-3.5 py-2 whitespace-pre-wrap"
                  style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
                >
                  {m.text}
                </div>
              ) : (
                <div
                  key={m.id}
                  className="max-w-[90%] self-start rounded-2xl rounded-bl-md px-3.5 py-2"
                  style={{ background: "var(--ai-bg)", border: "1px solid var(--ai-line)" }}
                >
                  <Markdown>{m.text}</Markdown>
                </div>
              ),
            )}
            {pending && (
              <div className="self-start px-1 text-[12.5px]" style={{ color: "var(--muted)" }}>
                답을 쓰는 중...
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={submit}
        className={`flex items-end gap-2 ${compact ? "p-3" : "px-6 pt-3 pb-6"}`}
        style={{ borderTop: "1px solid var(--line)" }}
      >
        <textarea
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="메시지 입력 (Shift+Enter 줄바꿈)"
          className="max-h-32 min-h-10 flex-1 resize-none rounded-2xl px-3.5 py-2.5 outline-none"
          style={{ background: "var(--search-bg)", color: "var(--text)" }}
        />
        <button
          type="submit"
          disabled={!draft.trim() || pending}
          className="h-10 rounded-2xl px-4 font-bold disabled:opacity-50"
          style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
        >
          보내기
        </button>
      </form>
    </div>
  );
}
