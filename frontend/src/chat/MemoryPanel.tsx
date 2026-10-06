import { useChat } from "./chat";

/** 헤더의 기억 버튼. 누르면 대화 자리에 기억 목록이 뜬다. */
export function MemoryToggle({ className = "" }: { className?: string }) {
  const { memories, memoryOpen, setMemoryOpen } = useChat();
  return (
    <button
      type="button"
      onClick={() => setMemoryOpen(!memoryOpen)}
      aria-pressed={memoryOpen}
      title="AI가 기억하는 것"
      className={className}
      style={{ color: memoryOpen ? "var(--accent)" : "var(--muted)", fontWeight: memoryOpen ? 700 : undefined }}
    >
      🧠 기억 {memories.length}
    </button>
  );
}

/** AI가 기억하는 것. 채팅에서 말하면 쌓이고, 여기서 지운다. */
export function MemoryPanel({ compact = false }: { compact?: boolean }) {
  const { memories, deleteMemory, setMemoryOpen } = useChat();

  return (
    <div className={`min-h-0 flex-1 overflow-y-auto ${compact ? "px-4 py-3" : "px-6 py-6"}`}>
      <div className="flex items-baseline gap-2">
        <span className="font-bold" style={{ color: "var(--text)" }}>
          AI가 기억하는 것
        </span>
        <button
          type="button"
          onClick={() => setMemoryOpen(false)}
          className="ml-auto text-[12.5px]"
          style={{ color: "var(--link)" }}
        >
          ← 대화로
        </button>
      </div>
      <p className="mt-1 text-[12.5px]" style={{ color: "var(--muted)" }}>
        새 대화를 시작해도 남아서 답을 고르는 데 쓰입니다. 학과, 학번, 휴학 여부처럼 채팅에서 말한
        내용이 쌓입니다.
      </p>

      {memories.length === 0 ? (
        <div className="mt-6 text-center text-[12.5px]" style={{ color: "var(--muted)" }}>
          아직 기억하는 것이 없습니다.
          <br />
          예: "나 소프트웨어학부 22학번이야"
        </div>
      ) : (
        <ul className="mt-4 flex flex-col gap-2">
          {memories.map((m) => (
            <li
              key={m.id}
              className="flex items-start gap-2 rounded-xl px-3 py-2"
              style={{ border: "1px solid var(--line)" }}
            >
              <span className="min-w-0 flex-1 text-[13px]" style={{ color: "var(--body-text)" }}>
                {m.content}
              </span>
              <button
                type="button"
                onClick={() => deleteMemory(m.id)}
                className="shrink-0 px-1 text-[12px]"
                style={{ color: "var(--muted)" }}
                aria-label={`기억 지우기: ${m.content}`}
                title="지우기"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
