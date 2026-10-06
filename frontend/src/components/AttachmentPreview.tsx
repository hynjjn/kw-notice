import { useEffect, useRef, useState } from "react";
import type { Attachment } from "../api/types";
import { extOf, kindOf } from "./previewKind";

/** 미리보기 한 건. 첨부 자체일 수도, zip 안의 파일일 수도 있다. */
interface Doc {
  src: string;
  name: string;
  ext: string;
  /** zip 이면 목록을 받아 올 첨부 id */
  attachmentId?: number;
}

const docOf = (a: Attachment): Doc => ({
  src: `/api/attachments/${a.id}/file`,
  name: a.filename,
  ext: a.file_ext ?? extOf(a.filename),
  attachmentId: a.id,
});

const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

function Message({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid h-full place-items-center p-8 text-center text-[13px]" style={{ color: "var(--muted)" }}>
      {children}
    </div>
  );
}

function Failed({ error }: { error: string }) {
  return (
    <Message>
      이 문서는 미리 볼 수 없습니다. 다운로드해서 열어 주세요.
      <br />({error})
    </Message>
  );
}

async function fetchBytes(src: string) {
  const res = await fetch(src);
  if (!res.ok) {
    // 서버가 {"detail": "..."} 로 사유를 주면 그걸 보인다(너무 큰 파일, 암호 걸린 파일 등).
    const detail = await res
      .json()
      .then((b: { detail?: unknown }) => (typeof b.detail === "string" ? b.detail : null))
      .catch(() => null);
    throw new Error(detail ?? `파일을 받지 못했습니다 (${res.status})`);
  }
  return new Uint8Array(await res.arrayBuffer());
}

/** 문서를 한 쪽씩 이미지(Blob)로 바꾸는 렌더러. 무거운 라이브러리라 쓸 때 불러온다. */
const RENDERERS = {
  pdf: async function* (bytes: Uint8Array) {
    yield* (await import("./pdf")).renderPdf(bytes);
  },
  // 문서에서 나온 SVG 를 innerHTML 로 넣지 않는다. <img> 로 띄우면
  // 그 안의 스크립트나 외부 참조가 실행되지 않는다.
  hwp: async function* (bytes: Uint8Array) {
    for await (const svg of (await import("./hwp")).renderHwp(bytes)) {
      yield new Blob([svg], { type: "image/svg+xml" });
    }
  },
};

function Pages({ src, kind }: { src: string; kind: keyof typeof RENDERERS }) {
  const [urls, setUrls] = useState<string[]>([]);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const made: string[] = [];
    (async () => {
      try {
        const bytes = await fetchBytes(src);
        for await (const page of RENDERERS[kind](bytes)) {
          // 닫거나 다른 첨부로 넘어가면 break 가 렌더러의 finally 를 불러 문서를 놓아 준다.
          if (cancelled) break;
          const url = URL.createObjectURL(page);
          made.push(url);
          setUrls((prev) => [...prev, url]);
        }
        if (!cancelled) setDone(true);
      } catch (e) {
        if (!cancelled) setError(errorText(e));
      }
    })();
    return () => {
      cancelled = true;
      made.forEach(URL.revokeObjectURL);
    };
  }, [src, kind]);

  if (error && urls.length === 0) return <Failed error={error} />;
  if (urls.length === 0) return <Message>문서를 그리는 중...</Message>;

  return (
    <div className="flex flex-col items-center gap-4 p-4" style={{ background: "var(--line-soft)" }}>
      {urls.map((u, i) => (
        <img
          key={u}
          src={u}
          alt={`${i + 1}쪽`}
          className="w-full max-w-[820px] shadow-sm"
          style={{ background: "#fff" }}
        />
      ))}
      {!done && (
        <div className="py-2 text-[12.5px]" style={{ color: "var(--muted)" }}>
          {error ? `${urls.length + 1}쪽부터 그리지 못했습니다. 다운로드해서 열어 주세요.` : `${urls.length + 1}쪽 그리는 중...`}
        </div>
      )}
    </div>
  );
}

/** docx, pptx 처럼 라이브러리가 DOM 을 직접 만드는 형식. */
function DomView({ src, kind }: { src: string; kind: "docx" | "pptx" }) {
  const ref = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"loading" | "ok" | string>("loading");

  useEffect(() => {
    let cancelled = false;
    let dispose: (() => void) | undefined;
    // 라이브러리가 그리는 동안 화면에 붙어 있어야 폭을 잰다(hidden 이면 0 이 나온다).
    const host = document.createElement("div");
    ref.current?.replaceChildren(host);
    (async () => {
      try {
        const bytes = await fetchBytes(src);
        const office = await import("./office");
        if (cancelled) return;
        if (kind === "docx") await office.renderDocx(bytes, host);
        else dispose = await office.renderPptx(bytes, host);
        if (!cancelled) setState("ok");
      } catch (e) {
        if (!cancelled) setState(errorText(e));
      }
    })();
    return () => {
      cancelled = true;
      dispose?.();
      host.remove();
    };
  }, [src, kind]);

  return (
    <>
      {state === "loading" && <Message>문서를 그리는 중...</Message>}
      {state !== "loading" && state !== "ok" && <Failed error={state} />}
      <div ref={ref} className={`office-view office-${kind}`} hidden={state !== "loading" && state !== "ok"} />
    </>
  );
}

function SheetView({ src }: { src: string }) {
  const [sheets, setSheets] = useState<{ name: string; html: string }[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const bytes = await fetchBytes(src);
        const office = await import("./office");
        const parsed = office.renderXlsx(bytes).map(({ name, html }) => {
          const t = document.createElement("template");
          t.innerHTML = html;
          const wrap = document.createElement("div");
          wrap.append(t.content);
          office.scrub(wrap);
          return { name, html: wrap.innerHTML };
        });
        if (!cancelled) setSheets(parsed);
      } catch (e) {
        if (!cancelled) setError(errorText(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [src]);

  if (error) return <Failed error={error} />;
  if (!sheets) return <Message>표를 읽는 중...</Message>;
  if (sheets.length === 0) return <Message>빈 통합 문서입니다.</Message>;

  return (
    <div className="flex h-full flex-col">
      {sheets.length > 1 && (
        <div className="flex gap-1 overflow-x-auto px-3 pt-2" style={{ borderBottom: "1px solid var(--line)" }}>
          {sheets.map((s, i) => (
            <button
              key={s.name}
              type="button"
              className="preview-btn"
              style={i === active ? { background: "var(--sel)", color: "var(--text)" } : undefined}
              onClick={() => setActive(i)}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}
      {/* SheetJS 가 셀 값을 이스케이프하고, 위에서 scrub 도 한 번 더 거쳤다. */}
      <div className="sheet-view min-h-0 flex-1 overflow-auto p-3" dangerouslySetInnerHTML={{ __html: sheets[active].html }} />
    </div>
  );
}

interface ZipEntry {
  index: number;
  name: string;
  size: number;
}

// 서버의 MAX_ENTRY_BYTES 와 맞춘다. 이보다 크면 서버가 413 을 준다.
const MAX_ENTRY_BYTES = 50 * 1024 * 1024;

const formatSize = (n: number) =>
  n < 1024 ? `${n}B` : n < 1024 * 1024 ? `${(n / 1024).toFixed(0)}KB` : `${(n / 1024 / 1024).toFixed(1)}MB`;

function ZipView({ attachmentId }: { attachmentId: number }) {
  const [entries, setEntries] = useState<ZipEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<ZipEntry | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/attachments/${attachmentId}/entries`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`목록을 받지 못했습니다 (${res.status})`);
        return (await res.json()) as ZipEntry[];
      })
      .then((list) => !cancelled && setEntries(list))
      .catch((e) => !cancelled && setError(errorText(e)));
    return () => {
      cancelled = true;
    };
  }, [attachmentId]);

  if (error) return <Failed error={error} />;
  if (!entries) return <Message>압축 파일을 여는 중...</Message>;

  if (open) {
    const name = open.name.split("/").pop()!;
    return (
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-2 px-3 py-1.5 text-[12.5px]" style={{ borderBottom: "1px solid var(--line)" }}>
          <button type="button" className="preview-btn" onClick={() => setOpen(null)}>
            ‹ 목록
          </button>
          <span className="min-w-0 truncate" style={{ color: "var(--muted)" }}>
            {open.name}
          </span>
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          <Body doc={{ src: `/api/attachments/${attachmentId}/entries/${open.index}`, name, ext: extOf(name) }} />
        </div>
      </div>
    );
  }

  return (
    <ul className="p-3">
      {entries.map((e) => {
        const kind = kindOf(extOf(e.name));
        const tooBig = e.size > MAX_ENTRY_BYTES;
        const usable = kind && kind !== "zip" && !tooBig;
        return (
          <li key={e.index}>
            <button
              type="button"
              disabled={!usable}
              onClick={() => setOpen(e)}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-[13px] enabled:hover:bg-[var(--nav-hover)] disabled:opacity-50"
              title={usable ? "미리보기" : tooBig ? "미리 보기에는 너무 큰 파일" : "미리 볼 수 없는 형식"}
            >
              <span>{usable ? "👁" : "📄"}</span>
              {/* 폴더를 몇 겹 쌓은 zip 이 있다. 파일 이름을 먼저 보이고 경로는 작게 단다. */}
              <span className="min-w-0 flex-1">
                <span className="block truncate">{e.name.split("/").pop()}</span>
                {e.name.includes("/") && (
                  <span className="block truncate text-[11px]" style={{ color: "var(--faint)" }}>
                    {e.name.slice(0, e.name.lastIndexOf("/"))}
                  </span>
                )}
              </span>
              <span className="text-[11.5px]" style={{ color: "var(--faint)" }}>
                {formatSize(e.size)}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function Body({ doc }: { doc: Doc }) {
  switch (kindOf(doc.ext)) {
    case "pdf":
      return <Pages src={doc.src} kind="pdf" />;
    case "hwp":
      return <Pages src={doc.src} kind="hwp" />;
    case "image":
      return (
        <div className="grid min-h-full place-items-center p-4" style={{ background: "var(--line-soft)" }}>
          <img src={doc.src} alt={doc.name} className="max-w-full" />
        </div>
      );
    case "docx":
      return <DomView src={doc.src} kind="docx" />;
    case "pptx":
      return <DomView src={doc.src} kind="pptx" />;
    case "xlsx":
      return <SheetView src={doc.src} />;
    case "zip":
      return doc.attachmentId !== undefined ? (
        <ZipView attachmentId={doc.attachmentId} />
      ) : (
        <Message>압축 파일 안의 압축 파일은 미리 볼 수 없습니다.</Message>
      );
    default:
      return <Message>미리 볼 수 없는 형식입니다.</Message>;
  }
}

export function AttachmentPreview({
  attachments,
  index,
  onIndex,
  onClose,
}: {
  attachments: Attachment[];
  index: number;
  onIndex: (i: number) => void;
  onClose: () => void;
}) {
  const current = attachments[index];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowLeft" && index > 0) onIndex(index - 1);
      else if (e.key === "ArrowRight" && index < attachments.length - 1) onIndex(index + 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, attachments.length, onClose, onIndex]);

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center p-4"
      style={{ background: "rgba(0,0,0,.55)" }}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${current.filename} 미리보기`}
        className="flex h-full max-h-[92vh] w-full max-w-[960px] flex-col overflow-hidden rounded-2xl"
        style={{ background: "var(--surface)", border: "1px solid var(--line)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <header
          className="flex items-center gap-2 px-4 py-2.5 text-[13px]"
          style={{ borderBottom: "1px solid var(--line)" }}
        >
          {attachments.length > 1 && (
            <>
              <button type="button" className="preview-btn" disabled={index === 0} onClick={() => onIndex(index - 1)} aria-label="이전 첨부">
                ‹
              </button>
              <span style={{ color: "var(--muted)" }}>
                {index + 1}/{attachments.length}
              </span>
              <button
                type="button"
                className="preview-btn"
                disabled={index === attachments.length - 1}
                onClick={() => onIndex(index + 1)}
                aria-label="다음 첨부"
              >
                ›
              </button>
            </>
          )}
          <span className="min-w-0 flex-1 truncate font-bold">{current.filename}</span>
          <a className="preview-btn" href={current.url} target="_blank" rel="noreferrer">
            다운로드 ↓
          </a>
          <button type="button" className="preview-btn" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-auto">
          {current.has_file ? (
            <Body key={current.id} doc={docOf(current)} />
          ) : (
            <Message>서버에 받아 둔 파일이 없습니다. 다운로드해서 열어 주세요.</Message>
          )}
        </div>
      </div>
    </div>
  );
}
