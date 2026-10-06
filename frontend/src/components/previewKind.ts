import type { Attachment } from "../api/types";

export type Kind = "pdf" | "image" | "hwp" | "docx" | "xlsx" | "pptx" | "zip";

// 옛 바이너리 형식(doc, ppt)은 브라우저에서 읽을 라이브러리가 마땅치 않아 뺐다.
// xls 는 SheetJS 가 읽는다.
const KINDS: Record<string, Kind> = {
  pdf: "pdf",
  png: "image",
  jpg: "image",
  jpeg: "image",
  gif: "image",
  webp: "image",
  hwp: "hwp",
  hwpx: "hwp",
  docx: "docx",
  xlsx: "xlsx",
  xls: "xlsx",
  pptx: "pptx",
  zip: "zip",
};

export const extOf = (name: string) => (name.includes(".") ? name.split(".").pop()!.toLowerCase() : "");

/** 브라우저에서 그릴 수 있는 형식이면 미리보기 종류를 준다. */
export function kindOf(ext: string | null): Kind | null {
  return KINDS[(ext ?? "").toLowerCase()] ?? null;
}

/** 서버에 받아 둔 파일이 있고 그릴 수 있는 형식인 첨부만 미리보기를 연다. */
export function previewKind(a: Attachment): Kind | null {
  return a.has_file ? kindOf(a.file_ext) : null;
}
