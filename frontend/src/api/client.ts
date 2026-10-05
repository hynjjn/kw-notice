import type { ChatReply, Digest, NoticeDetail, NoticeList, NoticeQuery, Stats } from "./types";

// vite 의 proxy(개발), CloudFront 의 behavior(배포)가 이 경로를 백엔드로 넘긴다.
const BASE = "/api";

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** FastAPI 는 {"detail": "..."} 로 오류를 준다. 사람이 읽을 문장만 꺼낸다. */
function detailOf(body: string): string {
  try {
    const detail = (JSON.parse(body) as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  } catch {
    // JSON 이 아니면 받은 그대로 쓴다.
  }
  return body;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, detailOf(body) || res.statusText);
  }
  return res.json() as Promise<T>;
}

function toQuery(params: NoticeQuery): string {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    // false 는 의미 있는 값이다(pinned=false = 고정 제외). undefined 만 걸러낸다.
    if (value !== undefined && value !== "") sp.set(key, String(value));
  }
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  notices: (params: NoticeQuery) =>
    request<NoticeList>(`/notices${toQuery(params)}`),
  notice: (id: number) => request<NoticeDetail>(`/notices/${id}`),
  summarize: (id: number) =>
    request<NoticeDetail>(`/notices/${id}/summary`, { method: "POST" }),
  stats: () => request<Stats>("/stats"),
  chat: (messages: { role: "user" | "assistant"; text: string; notice_id?: number }[]) =>
    request<ChatReply>("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    }),
  digest: (date: string) => request<Digest>(`/digests/${date}`),
  setRead: (id: number, value: boolean) =>
    request<void>(`/notices/${id}/read?value=${value}`, { method: "PUT" }),
  setStar: (id: number, value: boolean) =>
    request<void>(`/notices/${id}/star?value=${value}`, { method: "PUT" }),
};

export { ApiError };
