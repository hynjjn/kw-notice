// MS Office 문서(docx, pptx, xlsx)를 HTML 로 그린다. PDF, HWP 와 달리
// 이 라이브러리들은 이미지가 아니라 DOM 을 만든다. 무거워서 처음 열 때만
// 동적 import 로 불러온다.
import { renderAsync } from "docx-preview";
import { init as initPptx } from "pptx-preview";
import { read, utils } from "xlsx";

/**
 * 문서에서 온 DOM 에서 실행될 수 있는 것을 걷어 낸다.
 *
 * 라이브러리들이 문서 내용을 innerHTML 이 아니라 createElement 로 옮기긴 하지만,
 * 하이퍼링크 주소나 문서에 심은 HTML 조각(altChunk)이 그대로 넘어올 수 있다.
 */
function scrub(root: HTMLElement) {
  root.querySelectorAll("script, iframe, object, embed, link, meta, base, form").forEach((el) => el.remove());
  for (const el of root.querySelectorAll("*")) {
    for (const attr of [...el.attributes]) {
      const name = attr.name.toLowerCase();
      if (name.startsWith("on")) el.removeAttribute(attr.name);
      else if (
        (name === "href" || name === "src" || name === "xlink:href" || name === "action") &&
        /^\s*(javascript|vbscript|data:text\/html)/i.test(attr.value)
      )
        el.removeAttribute(attr.name);
    }
    if (el instanceof HTMLAnchorElement) {
      el.target = "_blank";
      el.rel = "noreferrer noopener";
    }
  }
}

export async function renderDocx(bytes: Uint8Array, container: HTMLElement) {
  await renderAsync(bytes, container, container, {
    // 문서에 박힌 HTML 조각은 iframe 으로 그린다. 출처를 믿을 수 없으니 끈다.
    renderAltChunks: false,
    // blob URL 은 놓아 줄 때를 알 수 없어서 이미지를 data URL 로 넣는다.
    useBase64URL: true,
    breakPages: true,
    // 미리보기 칸이 문서 폭보다 좁을 때 가로 스크롤 대신 줄여 보이게 CSS 가 맞춘다.
    className: "docx",
  });
  // 문서의 페이지 배경색(w:background)은 Word 에서도 "배경 표시"를 켜야 보인다.
  // docx-preview 는 이를 무조건 칠해서, 검정으로 저장된 양식이 새까만 종이로 나온다.
  container.querySelectorAll<HTMLElement>("section.docx").forEach((page) => page.style.removeProperty("background-color"));
  scrub(container);
}

export async function renderPptx(bytes: Uint8Array, container: HTMLElement) {
  // 슬라이드는 이 폭에 맞춰 축소된다. 폭을 0 으로 재면 배율이 음수가 되어 아무것도 안 보인다.
  const width = Math.max(320, Math.min(container.clientWidth, 900));
  const previewer = initPptx(container, { width, mode: "list" });
  await previewer.preview(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer);
  scrub(container);
  return () => previewer.destroy();
}

/** 시트마다 표 HTML 을 돌려준다. SheetJS 가 셀 값을 이스케이프한다. */
export function renderXlsx(bytes: Uint8Array): { name: string; html: string }[] {
  // 수식 결과는 파일에 캐시된 값을 쓴다. 외부 링크나 매크로는 읽지 않는다.
  const book = read(bytes, { type: "array", cellFormula: false, cellHTML: false });
  return book.SheetNames.map((name) => ({
    name,
    html: utils.sheet_to_html(book.Sheets[name], { header: "", footer: "" }),
  }));
}

/** xlsx 표를 넣은 뒤에도 같은 정리를 거친다. */
export { scrub };
