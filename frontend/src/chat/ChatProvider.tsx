import { useCallback, useMemo, useState, type ReactNode } from "react";
import { ChatContext, type ChatMessage } from "./chat";

let nextId = 1;

/**
 * 대화를 앱 전체에서 하나로 들고 있는다. 떠 있는 창에서 묻다가 전용 페이지로
 * 넓혀도 대화가 이어져야 하기 때문이다.
 *
 * 아직 백엔드가 없다. send 는 자리표시 답만 붙인다. 다음 커밋에서 API 로 바꾼다.
 */
export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [floatingOpen, setFloatingOpen] = useState(false);

  const send = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages((prev) => [...prev, { id: nextId++, role: "user", text: trimmed }]);
    setPending(true);
    window.setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId++,
          role: "assistant",
          text: "아직 AI 채팅이 연결되지 않았습니다. 곧 공지와 첨부파일 내용을 바탕으로 답해 드릴게요.",
        },
      ]);
      setPending(false);
    }, 400);
  }, []);

  const reset = useCallback(() => setMessages([]), []);

  const value = useMemo(
    () => ({ messages, pending, send, reset, floatingOpen, setFloatingOpen }),
    [messages, pending, send, reset, floatingOpen],
  );
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
