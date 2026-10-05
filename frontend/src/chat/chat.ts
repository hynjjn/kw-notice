import { createContext, useContext } from "react";

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
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
