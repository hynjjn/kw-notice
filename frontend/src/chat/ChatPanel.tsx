import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import { Markdown } from "../components/Markdown";
import { noticeHref } from "../links";
import { useChat } from "./chat";

const SUGGESTIONS = [
  "이번 주에 마감되는 장학금 알려줘",
  "외국인 유학생 대상 공지만 모아줘",
  "통장사본 내야 하는 공지가 뭐야?",
];

// 공지를 열어 둔 채 물을 때. "이 공지"는 서버가 열린 공지로 풀어 준다.
const NOTICE_SUGGESTIONS = [
  "이 공지 마감 언제야?",
  "신청 방법이랑 필요한 서류 정리해줘",
  "비슷한 공지 더 있어?",
];

/** 답이 오기 전까지 답 말풍선 자리를 잡아 둔다. 도구 호출 때문에 수 초 걸린다. */
function AnswerSkeleton() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex w-[75%] flex-col gap-2 self-start rounded-2xl rounded-bl-md px-3.5 py-3"
      style={{ background: "var(--ai-bg)", border: "1px solid var(--ai-line)" }}
    >
      <span className="text-[12px] font-bold" style={{ color: "var(--unread)" }}>
        ✨ 생각 중...
      </span>
      <span className="skeleton-line w-full" />
      <span className="skeleton-line w-[85%]" />
      <span className="skeleton-line w-[60%]" />
    </div>
  );
}

/** 대화 목록과 입력창. 떠 있는 창과 전용 페이지가 같이 쓴다. */
export function ChatPanel({ compact = false }: { compact?: boolean }) {
  const { messages, pending, send, currentNotice, attachNotice } = useChat();
  const activeId = currentNotice?.id ?? null;
  const suggestions = currentNotice && attachNotice ? NOTICE_SUGGESTIONS : SUGGESTIONS;
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
              {suggestions.map((s) => (
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
                <div key={m.id} className="flex max-w-[85%] flex-col items-end gap-1 self-end">
                  {m.notice && (
                    <Link
                      to={noticeHref(m.notice.id)}
                      title={m.notice.title}
                      className="max-w-full truncate text-[11px]"
                      style={{ color: "var(--muted)" }}
                    >
                      📄 {m.notice.title}
                    </Link>
                  )}
                  <div
                    className="rounded-2xl rounded-br-md px-3.5 py-2 whitespace-pre-wrap"
                    style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
                  >
                    {m.text}
                  </div>
                </div>
              ) : (
                <div key={m.id} className="flex max-w-[90%] flex-col gap-1.5 self-start">
                  <div
                    className="rounded-2xl rounded-bl-md px-3.5 py-2"
                    style={
                      m.error
                        ? { border: "1px solid var(--line)", color: "var(--accent)" }
                        : { background: "var(--ai-bg)", border: "1px solid var(--ai-line)" }
                    }
                  >
                    {m.error ? m.text : <Markdown activeNoticeId={activeId}>{m.text}</Markdown>}
                  </div>
                  {m.notices && m.notices.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {m.notices.map((n) => (
                        <Link
                          key={n.id}
                          to={noticeHref(n.id)}
                          title={n.id === activeId ? `지금 열려 있는 공지: ${n.title}` : n.title}
                          className="max-w-full truncate rounded-full px-2.5 py-1 text-[11.5px]"
                          style={
                            n.id === activeId
                              ? {
                                  border: "1px solid var(--accent)",
                                  background: "var(--accent-soft)",
                                  color: "var(--accent)",
                                  fontWeight: 700,
                                }
                              : { border: "1px solid var(--line)", color: "var(--body-text)" }
                          }
                        >
                          {n.id === activeId ? "👀" : "📄"} {n.title}
                          {n.deadline_at && (
                            <span style={{ color: "var(--accent)" }}> · ~{n.deadline_at.slice(5)}</span>
                          )}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ),
            )}
            {pending && <AnswerSkeleton />}
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
