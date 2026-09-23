import type { Digest } from "../api/types";

export function DigestCard({ digest, date }: { digest?: Digest; date: string }) {
  if (!digest) return null;
  const [headline, ...rest] = digest.summary_md.split("\n").filter(Boolean);

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
      <p className="mb-1.5" style={{ color: "var(--body-text)" }}>
        {headline}
      </p>
      <ul className="list-disc pl-4.5" style={{ color: "var(--body-text)" }}>
        {rest.map((line) => (
          <li key={line} className="my-0.5">
            {line.replace(/^-\s*/, "")}
          </li>
        ))}
      </ul>
    </div>
  );
}
