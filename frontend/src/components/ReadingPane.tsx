import type { NoticeDetail } from "../api/types";

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
          <div className="whitespace-pre-line">{notice.ai_summary}</div>
          {notice.deadline_at && (
            <div className="mt-2 text-[12.5px] font-bold" style={{ color: "var(--accent)" }}>
              마감 {notice.deadline_at}
            </div>
          )}
        </div>
      ) : (
        <div className="my-4 text-[12.5px]" style={{ color: "var(--faint)" }}>
          아직 요약이 없습니다. <code>python -m app.summarize</code> 를 돌리면 생깁니다.
        </div>
      )}

      {notice.body_text ? (
        <div
          className="text-[14.5px] leading-[1.85] whitespace-pre-line"
          style={{ color: "var(--body-text)" }}
        >
          {notice.body_text}
        </div>
      ) : (
        <div className="text-[13px]" style={{ color: "var(--faint)" }}>
          본문 글자가 없는 공지입니다. 아래 이미지가 내용입니다.
        </div>
      )}

      {/* 본문이 포스터 이미지뿐인 공지가 전체의 23%다. */}
      {notice.inline_image_urls?.map((src) => (
        <img key={src} className="my-3 max-w-full rounded-lg" src={src} alt="" loading="lazy" />
      ))}

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
