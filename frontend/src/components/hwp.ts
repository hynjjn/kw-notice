// HWP/HWPX 를 페이지별 SVG 로 그린다. WASM 이 10MB 라서 이 모듈은
// 한글 파일 미리보기를 처음 열 때 동적 import 로만 불러온다.
import init, { HwpDocument } from "@rhwp/core";
import wasmUrl from "@rhwp/core/rhwp_bg.wasm?url";

let ready: Promise<unknown> | null = null;

function ensureInit() {
  if (!ready) {
    // rhwp 가 줄 나눔을 계산할 때 글자 폭을 브라우저에 묻는다. 없으면 init 전에 넣어야 한다.
    let ctx: CanvasRenderingContext2D | null = null;
    let lastFont = "";
    (globalThis as { measureTextWidth?: unknown }).measureTextWidth = (
      font: string,
      text: string,
    ) => {
      ctx ??= document.createElement("canvas").getContext("2d")!;
      if (font !== lastFont) {
        ctx.font = font;
        lastFont = font;
      }
      return ctx.measureText(text).width;
    };
    ready = init({ module_or_path: wasmUrl }).catch((e) => {
      ready = null;
      throw e;
    });
  }
  return ready;
}

/** 한 쪽씩 SVG 문자열로 넘긴다. */
export async function* renderHwp(bytes: Uint8Array): AsyncGenerator<string> {
  await ensureInit();
  const doc = new HwpDocument(bytes);
  try {
    for (let i = 0; i < doc.pageCount(); i++) {
      yield doc.renderPageSvg(i);
      // 쪽 사이에 한 번씩 메인 스레드를 내준다. 그래야 그린 쪽이 바로 화면에 뜬다.
      await new Promise((r) => setTimeout(r));
    }
  } finally {
    doc.free();
  }
}
