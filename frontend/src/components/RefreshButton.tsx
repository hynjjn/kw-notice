import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import type { RefreshStatus } from "../api/types";
import { useRefreshStatus, useStartRefresh } from "../hooks";

function ago(iso: string | null): string {
  if (!iso) return "아직 없음";
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (min < 1) return "방금";
  if (min < 60) return `${min}분 전`;
  const hours = Math.round(min / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.round(hours / 24)}일 전`;
}

function resultText(s: RefreshStatus): string {
  if (s.state === "failed") return "가져오지 못했습니다";
  const parts = [s.new > 0 ? `새 공지 ${s.new}건` : "새 공지 없음"];
  if (s.updated > 0) parts.push(`수정 ${s.updated}건`);
  if (s.failed_sources.length > 0) parts.push("일부 출처 실패");
  return parts.join(", ");
}

/** 헤더의 "새 공지 가져오기". 서버가 백그라운드로 수집하고, 끝나면 목록을 새로 고친다. */
export function RefreshButton() {
  const qc = useQueryClient();
  const status = useRefreshStatus();
  const start = useStartRefresh();
  const data = status.data;
  const running = data?.state === "running" || start.isPending;

  // 결과는 잠시 보여 주고 거둔다. 버튼 옆에 계속 남아 있으면 지난 결과인지 헷갈린다.
  const [result, setResult] = useState<string | null>(null);
  const prevState = useRef(data?.state);
  useEffect(() => {
    const prev = prevState.current;
    prevState.current = data?.state;
    if (prev !== "running" || !data || data.state === "running") return;

    qc.invalidateQueries({ queryKey: ["notices"] });
    qc.invalidateQueries({ queryKey: ["stats"] });
    qc.invalidateQueries({ queryKey: ["notice"] });
    setResult(resultText(data));
  }, [data, qc]);

  useEffect(() => {
    if (!result) return;
    const timer = window.setTimeout(() => setResult(null), 8_000);
    return () => window.clearTimeout(timer);
  }, [result]);

  const title = running
    ? "학교 서버에 요청 간격을 두고 가져오느라 몇 분 걸립니다"
    : `마지막으로 가져온 시각: ${ago(data?.last_crawled_at ?? null)}`;

  return (
    <div className="flex items-center gap-2.5 text-[12.5px]">
      {result && !running && (
        <span
          role="status"
          className="rounded-full px-2.5 py-1 font-bold"
          style={
            data?.state === "failed"
              ? { background: "var(--accent-soft)", color: "var(--accent)" }
              : { background: "var(--ok-bg)", color: "var(--ok-text)" }
          }
        >
          {result}
        </span>
      )}
      {running && (
        <span role="status" style={{ color: "var(--muted)" }}>
          {data?.stage ?? "시작하는 중"}...
        </span>
      )}
      <button
        type="button"
        onClick={() => {
          setResult(null);
          start.mutate();
        }}
        disabled={running}
        title={title}
        className="flex h-9 items-center gap-1.5 rounded-full px-3.5 font-bold disabled:cursor-progress"
        style={{ border: "1px solid var(--line)", color: "var(--text)" }}
      >
        <span className={running ? "spin" : undefined} aria-hidden>
          ↻
        </span>
        {running ? "가져오는 중" : "새 공지 가져오기"}
      </button>
    </div>
  );
}
