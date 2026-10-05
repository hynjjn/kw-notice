import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * AI 가 쓴 마크다운을 그린다. 원시 HTML 은 react-markdown 이 기본으로 버리므로
 * 모델 출력에 태그가 섞여도 그대로 실리지 않는다.
 * remark-gfm 이 맨 URL 도 링크로 바꿔 준다. 예전 요약은 URL 을 평문으로 담고 있다.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
