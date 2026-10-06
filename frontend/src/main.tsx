import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App";
import { ChatProvider } from "./chat/ChatProvider";
import { ChatPage } from "./pages/ChatPage";
// 쓰는 글자가 든 조각만 받는 dynamic subset 판. 한글 전체(수 MB)를 한 번에 받지 않는다.
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 공지는 하루 한 번 갱신된다. 창을 옮길 때마다 다시 받을 이유가 없다.
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChatProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<App />} />
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </BrowserRouter>
      </ChatProvider>
    </QueryClientProvider>
  </StrictMode>,
);
