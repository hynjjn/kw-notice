import type { NoticeDetail } from "../api/types";
import { useSummarize } from "../hooks";
import { Markdown } from "./Markdown";

function Meta({ notice }: { notice: NoticeDetail }) {
  const bits = [
    notice.author_dept ?? notice.source_name,
    `작성 ${notice.posted_at}`,
    notice.modified_at_source && notice.modified_at_source !== notice.posted_at
      ? `수정 ${notice.modified_at_source}`
      : null,
    `조회 ${notice.view_count.toLocaleString()}`,
    notice.attachment_count > 0 ? `📎 ${notice.attachment_count}` : null,
  ].filter(Boolean) as string[];

  return (
    <div
      className="flex flex-wrap items-center gap-2.5 pb-3.5 text-[12.5px]"
      style={{ borderBottom: "1px solid var(--line)", color: "var(--muted)" }}
    >
      {notice.category && <span className="chip">{notice.category}</span>}
      {bits.map((b) => (
        <span key={b}>{b}</span>
      ))}
      <a
        className="ml-auto"
        style={{ color: "var(--unread)" }}
        href={notice.url}
        target="_blank"
        rel="noreferrer"
      >
        원문 보기 ↗
      </a>
    </div>
  );
}

function SummarizeButton({ notice }: { notice: NoticeDetail }) {
  const summarize = useSummarize();
  // 다른 공지로 옮기면 이전 공지의 진행 상태나 오류를 보여 주지 않는다.
  const mine = summarize.variables === notice.id;
  const pending = mine && summarize.isPending;
  const error = mine && summarize.isError ? summarize.error : null;

  return (
    <div className="my-4 flex flex-wrap items-center gap-3 text-[12.5px]">
      <button
        type="button"
        disabled={pending}
        onClick={() => summarize.mutate(notice.id)}
        className="rounded-xl px-3 py-2 font-bold disabled:opacity-60"
        style={{
          background: "var(--ai-bg)",
          border: "1px solid var(--ai-line)",
          color: "var(--unread)",
        }}
      >
        {pending ? "요약하는 중..." : "✨ AI 요약 만들기"}
      </button>
      {error && (
        <span style={{ color: "var(--accent)" }}>요약하지 못했습니다. {error.message}</span>
      )}
    </div>
  );
}

export function ReadingPane({
  notice,
  loading,
}: {
  notice?: NoticeDetail;
  loading: boolean;
}) {
  if (loading) {
    return <div className="p-8" style={{ color: "var(--muted)" }}>불러오는 중...</div>;
  }
  if (!notice) {
    return (
      <div className="grid h-full place-items-center" style={{ color: "var(--faint)" }}>
        왼쪽에서 공지를 고르세요
      </div>
    );
  }

  return (
    <article className="overflow-y-auto px-8 pt-5 pb-16">
      <h1 className="mb-1.5 text-[21px] leading-snug font-bold tracking-tight">
        {notice.title}
      </h1>
      <Meta notice={notice} />

      {notice.ai_summary ? (
        <div
          className="my-4 rounded-2xl px-4 py-3.5"
          style={{ background: "var(--ai-bg)", border: "1px solid var(--ai-line)" }}
        >
          <h4 className="mb-1.5 text-xs font-extrabold" style={{ color: "var(--unread)" }}>
            ✨ AI 요약 {notice.attachment_count > 0 && "(첨부파일 포함)"}
          </h4>
          <Markdown>{notice.ai_summary}</Markdown>
          {notice.deadline_at && (
            <div className="mt-2 text-[12.5px] font-bold" style={{ color: "var(--accent)" }}>
              마감 {notice.deadline_at}
            </div>
          )}
        </div>
      ) : notice.body_text?.trim() || notice.inline_image_urls?.length ? (
        <SummarizeButton notice={notice} />
      ) : null}

      {/* 서버에서 nh3 로 정제한 HTML 이다. script, 이벤트 핸들러, 글자색은
          이미 걷혔다. 평문으로 바꿔 보여 주면 굵기와 크기가 사라지고,
          본문 중간에 있던 포스터가 전부 글 뒤로 밀린다. */}
      {notice.body_html ? (
        <div
          className="notice-body"
          dangerouslySetInnerHTML={{ __html: notice.body_html }}
        />
      ) : notice.body_text ? (
        <div
          className="text-[14.5px] leading-[1.85] whitespace-pre-line"
          style={{ color: "var(--body-text)" }}
        >
          {notice.body_text}
        </div>
      ) : (
        <div className="text-[13px]" style={{ color: "var(--faint)" }}>
          본문을 불러오지 못했습니다.
        </div>
      )}

      {notice.attachments.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-2.5">
          {notice.attachments.map((a) => (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-[12.5px]"
              style={{ border: "1px solid var(--line)", background: "var(--surface)" }}
            >
              📄 {a.filename}
              {a.has_text && (
                <span
                  className="rounded-full px-1.5 py-px text-[10px] font-bold"
                  style={{ background: "var(--ok-bg)", color: "var(--ok-text)" }}
                >
                  본문 추출됨
                </span>
              )}
            </a>
          ))}
        </div>
      )}
    </article>
  );
}
