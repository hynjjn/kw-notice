// PDF 를 페이지별 PNG 로 그린다. iframe 에 맡기면 PDF 뷰어가 없는 브라우저
// (일부 webview, 모바일)에서 빈 칸이 되거나 다운로드로 넘어간다.
// pdf.js 도 무거워서 PDF 미리보기를 처음 열 때만 동적 import 로 불러온다.
import { getDocument, GlobalWorkerOptions, version } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

GlobalWorkerOptions.workerSrc = workerUrl;

// 글꼴을 심지 않은 한글 PDF 는 CMap 이 있어야 글자가 나온다.
// 디렉터리째 번들에 넣을 방법이 마땅치 않아 같은 버전의 CDN 사본을 쓴다.
const CDN = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${version}`;

// 미리보기 칸의 최대 폭. 레티나에서는 2배로 그린다.
const PAGE_WIDTH = 820;

/** 한 쪽씩 그려 넘긴다. 슬라이드 수십 장짜리도 있어서 다 그릴 때까지 기다리게 하지 않는다. */
export async function* renderPdf(bytes: Uint8Array): AsyncGenerator<Blob> {
  const task = getDocument({
    data: bytes,
    cMapUrl: `${CDN}/cmaps/`,
    cMapPacked: true,
    standardFontDataUrl: `${CDN}/standard_fonts/`,
  });
  try {
    const doc = await task.promise;
    const width = PAGE_WIDTH * Math.min(window.devicePixelRatio || 1, 2);
    for (let i = 1; i <= doc.numPages; i++) {
      const page = await doc.getPage(i);
      const base = page.getViewport({ scale: 1 });
      const viewport = page.getViewport({ scale: width / base.width });
      const canvas = document.createElement("canvas");
      canvas.width = Math.ceil(viewport.width);
      canvas.height = Math.ceil(viewport.height);
      // 기본(display) intent 는 requestAnimationFrame 으로 그리기를 쪼갠다.
      // 탭이 가려져 있으면 rAF 가 멈춰 미리보기가 영영 안 끝난다. print 는 rAF 를 쓰지 않는다.
      await page.render({ canvas, viewport, intent: "print" }).promise;
      page.cleanup();
      // PNG 는 이 크기에서 인코딩이 눈에 띄게 느리다. 글자 읽기에는 JPEG 로 충분하다.
      yield await new Promise<Blob>((resolve, reject) =>
        canvas.toBlob(
          (b) => (b ? resolve(b) : reject(new Error("페이지를 그리지 못했습니다"))),
          "image/jpeg",
          0.9,
        ),
      );
    }
  } finally {
    await task.destroy();
  }
}
