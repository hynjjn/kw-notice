"""내려받은 첨부가 확장자대로의 파일인지 확인한다.

학부 게시판은 없는 파일을 요청해도 404 를 주지 않는다. 200 에 이런 걸 실어 보낸다.

    <script> alert('없는파일입니다.2'); history.go(-1); </script>

75바이트짜리 HTML 이다. 확장자만 믿고 저장하면 `.pdf` 인 HTML 이 디스크에 쌓이고,
추출 단계에 가서야 엉뚱한 자리에서 터진다. 받는 자리에서 걸러야 한다.
"""

from __future__ import annotations

OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # hwp 5.x, doc, xls
ZIP = b"PK\x03\x04"  # hwpx, docx, xlsx, zip

MAGIC: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF",),
    "hwp": (OLE2,),
    "doc": (OLE2,),
    "xls": (OLE2,),
    "hwpx": (ZIP,),
    "docx": (ZIP,),
    "xlsx": (ZIP,),
    "pptx": (ZIP,),
    "zip": (ZIP,),
    "png": (b"\x89PNG",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF8",),
}

# 이보다 작으면 내용이 있을 수 없다.
MIN_BYTES = 100


def problem(ext: str | None, payload: bytes) -> str | None:
    """문제가 있으면 사유를, 멀쩡하면 None 을 돌려준다."""
    if len(payload) < MIN_BYTES:
        return f"응답이 {len(payload)}바이트뿐"

    head = payload[:200].lstrip()
    if head[:1] == b"<" or b"alert(" in head:
        # 서버가 200 으로 돌려주는 오류 안내 페이지다.
        return "파일 대신 HTML 오류 페이지가 옴"

    expected = MAGIC.get((ext or "").lower())
    if expected and not payload.startswith(expected):
        return f"{ext} 시그니처 불일치 (앞 4바이트: {payload[:4]!r})"

    return None
