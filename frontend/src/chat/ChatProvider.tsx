import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { ChatContext, type ChatMessage } from "./chat";

let nextId = 1;

/**
 * 대화를 앱 전체에서 하나로 들고 있는다. 떠 있는 창에서 묻다가 전용 페이지로
 * 넓혀도 대화가 이어져야 하기 때문이다.
 *
 * 서버는 대화를 저장하지 않는다. 보낼 때마다 지금까지의 대화를 통째로 싣는다.
 */
export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [floatingOpen, setFloatingOpen] = useState(false);
  // 답을 기다리는 동안 "새 대화"를 누르면 늦게 온 답이 새 대화에 끼어든다.
  // 대화마다 번호를 매겨 번호가 바뀌었으면 버린다.
  const conversation = useRef(0);
  // send 를 매번 새로 만들지 않으려고 최신 대화를 ref 로 들고 있는다.
  const latest = useRef<ChatMessage[]>([]);
  useEffect(() => {
    latest.current = messages;
  }, [messages]);

  const send = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const question: ChatMessage = { id: nextId++, role: "user", text: trimmed };
    const history = [...latest.current, question];
    setMessages(history);
    setPending(true);

    const mine = conversation.current;
    api
      .chat(history.filter((m) => !m.error).map(({ role, text }) => ({ role, text })))
      .then(
        (res): ChatMessage => ({
          id: nextId++,
          role: "assistant",
          text: res.reply,
          notices: res.notices,
        }),
        (err: Error): ChatMessage => ({
          id: nextId++,
          role: "assistant",
          text: `답을 받지 못했습니다. ${err.message}`,
          error: true,
        }),
      )
      .then((reply) => {
        if (conversation.current !== mine) return;
        setMessages((prev) => [...prev, reply]);
        setPending(false);
      });
  }, []);

  const reset = useCallback(() => {
    conversation.current += 1;
    setMessages([]);
    setPending(false);
  }, []);

  const value = useMemo(
    () => ({ messages, pending, send, reset, floatingOpen, setFloatingOpen }),
    [messages, pending, send, reset, floatingOpen],
  );
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
