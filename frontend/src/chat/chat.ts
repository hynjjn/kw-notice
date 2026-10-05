import { createContext, useContext } from "react";
import type { ChatNoticeRef } from "../api/types";

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  /** 답에 쓰인 공지. 답 아래에 바로가기로 보여 준다. */
  notices?: ChatNoticeRef[];
  /** 요청이 실패해서 붙인 안내문. 다음 요청의 대화 기록에는 싣지 않는다. */
  error?: boolean;
};

type ChatState = {
  messages: ChatMessage[];
  pending: boolean;
  send: (text: string) => void;
  reset: () => void;
  floatingOpen: boolean;
  setFloatingOpen: (open: boolean) => void;
};

export const ChatContext = createContext<ChatState | null>(null);

export function useChat(): ChatState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat 은 ChatProvider 안에서만 쓴다");
  return ctx;
}
