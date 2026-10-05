import type { Digest } from "../api/types";
import { Markdown } from "./Markdown";

export function DigestCard({ digest, date }: { digest?: Digest; date: string }) {
  if (!digest) return null;
  return (
    <div
      className="m-3 rounded-2xl px-4 py-3.5"
      style={{ background: "var(--digest-bg)", border: "1px solid var(--digest-line)" }}
    >
      <h3
        className="mb-2 flex items-center gap-1.5 text-[13px] font-extrabold"
        style={{ color: "var(--accent)" }}
      >
        ✨ {date} 요약
      </h3>
      <Markdown>{digest.summary_md}</Markdown>
    </div>
  );
}
