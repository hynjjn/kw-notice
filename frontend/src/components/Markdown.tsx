import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import { Link } from "react-router-dom";
import remarkGfm from "remark-gfm";
import { noticeHref } from "../links";

/** AI 채팅이 공지를 가리킬 때 쓰는 링크. [제목](notice:123) */
const NOTICE_LINK = /^notice:(\d+)$/;

/** notice: 는 우리가 정한 스킴이다. 기본 변환기는 모르는 스킴을 지우므로 따로 살린다. */
function urlTransform(url: string): string {
  return NOTICE_LINK.test(url) ? url : defaultUrlTransform(url);
}

/**
 * AI 가 쓴 마크다운을 그린다. 원시 HTML 은 react-markdown 이 기본으로 버리므로
 * 모델 출력에 태그가 섞여도 그대로 실리지 않는다.
 * remark-gfm 이 맨 URL 도 링크로 바꿔 준다. 예전 요약은 URL 을 평문으로 담고 있다.
 */
export function Markdown({
  children,
  activeNoticeId,
}: {
  children: string;
  /** 지금 열려 있는 공지. 이 공지를 가리키는 링크를 강조한다. */
  activeNoticeId?: number | null;
}) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={urlTransform}
        components={{
          a: ({ href, children }) => {
            const notice = href?.match(NOTICE_LINK);
            if (notice) {
              const id = Number(notice[1]);
              return (
                <Link
                  to={noticeHref(id)}
                  className={id === activeNoticeId ? "md-active" : undefined}
                  title={id === activeNoticeId ? "지금 열려 있는 공지" : undefined}
                >
                  {children}
                </Link>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
