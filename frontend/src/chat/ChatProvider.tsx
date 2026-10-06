import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Memory } from "../api/types";
import { ChatContext, type ChatMessage, type NoticeContext } from "./chat";

let nextId = 1;

/**
 * 대화를 앱 전체에서 하나로 들고 있는다. 떠 있는 창에서 묻다가 전용 페이지로
 * 넓혀도 대화가 이어져야 하기 때문이다.
 *
 * 서버는 대화를 저장하지 않는다. 보낼 때마다 지금까지의 대화를 통째로 싣는다.
 * 대화를 넘어 남는 것은 서버의 기억(memories)뿐이다.
 */
export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [floatingOpen, setFloatingOpen] = useState(false);
  const [currentNotice, setCurrentNoticeState] = useState<NoticeContext | null>(null);
  const [attachNotice, setAttachNotice] = useState(true);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryOpen, setMemoryOpen] = useState(false);

  const loadMemories = useCallback(() => {
    // 기억 목록을 못 받아도 채팅은 된다. 목록만 비어 보인다.
    api.memories().then(setMemories, () => {});
  }, []);
  useEffect(loadMemories, [loadMemories]);

  const deleteMemory = useCallback((id: number) => {
    api.deleteMemory(id).then(setMemories, () => loadMemories());
  }, [loadMemories]);

  const setCurrentNotice = useCallback((notice: NoticeContext | null) => {
    setCurrentNoticeState((prev) => {
      // 다른 공지를 열면 "이 공지 기준" 을 다시 켠다. 제목만 다시 들어온 경우는 그대로 둔다.
      if (prev?.id !== notice?.id) setAttachNotice(true);
      return notice;
    });
  }, []);

  const contextNotice = attachNotice ? currentNotice : null;
  const contextRef = useRef<NoticeContext | null>(null);
  useEffect(() => {
    contextRef.current = contextNotice;
  }, [contextNotice]);
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

    const question: ChatMessage = {
      id: nextId++,
      role: "user",
      text: trimmed,
      notice: contextRef.current ?? undefined,
    };
    const history = [...latest.current, question];
    setMessages(history);
    setPending(true);

    const mine = conversation.current;
    api
      .chat(
        history
          .filter((m) => !m.error)
          .map(({ role, text, notice }) => ({ role, text, notice_id: notice?.id })),
      )
      .then(
        (res): ChatMessage => {
          if (res.remembered.length > 0 || res.forgotten.length > 0) loadMemories();
          return {
            id: nextId++,
            role: "assistant",
            text: res.reply,
            notices: res.notices,
            remembered: res.remembered,
            forgotten: res.forgotten,
          };
        },
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
  }, [loadMemories]);

  const reset = useCallback(() => {
    conversation.current += 1;
    setMessages([]);
    setPending(false);
  }, []);

  const value = useMemo(
    () => ({
      messages,
      pending,
      send,
      reset,
      floatingOpen,
      setFloatingOpen,
      currentNotice,
      setCurrentNotice,
      attachNotice,
      setAttachNotice,
      memories,
      deleteMemory,
      memoryOpen,
      setMemoryOpen,
    }),
    [
      messages,
      pending,
      send,
      reset,
      floatingOpen,
      currentNotice,
      setCurrentNotice,
      attachNotice,
      memories,
      deleteMemory,
      memoryOpen,
    ],
  );
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
