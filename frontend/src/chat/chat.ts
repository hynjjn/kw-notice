import { createContext, useContext } from "react";
import type { ChatNoticeRef } from "../api/types";

/** 화면에 열려 있는 공지. 떠 있는 창의 질문에 맥락으로 붙는다. */
export type NoticeContext = { id: number; title: string };

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  /** 답에 쓰인 공지. 답 아래에 바로가기로 보여 준다. */
  notices?: ChatNoticeRef[];
  /** 이 질문을 보낼 때 열려 있던 공지. 사용자 메시지에만 붙는다. */
  notice?: NoticeContext;
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
  /** 지금 열려 있는 공지. 공지 화면(App)이 채우고, 떠나면 비운다. */
  currentNotice: NoticeContext | null;
  setCurrentNotice: (notice: NoticeContext | null) => void;
  /** 다음 질문에 열린 공지를 붙일지. 공지를 바꾸면 다시 켜진다. */
  attachNotice: boolean;
  setAttachNotice: (attach: boolean) => void;
};

export const ChatContext = createContext<ChatState | null>(null);

export function useChat(): ChatState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat 은 ChatProvider 안에서만 쓴다");
  return ctx;
}
