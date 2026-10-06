from __future__ import annotations

import mimetypes
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.config import settings
from app.models import Attachment

router = APIRouter(prefix="/attachments", tags=["attachments"])

# mimetypes 가 모르는 확장자. 프론트가 바이트를 받아 직접 그리므로
# 정확한 등록 타입이 아니어도 된다.
_EXTRA_TYPES = {
    "hwp": "application/x-hwp",
    "hwpx": "application/hwp+zip",
}

# zip 안의 파일 하나를 메모리에 풀어서 내준다. 압축 폭탄을 막는 상한이다.
MAX_ENTRY_BYTES = 50 * 1024 * 1024

# zip 의 UTF-8 플래그(general purpose bit 11).
_UTF8_FLAG = 0x800


def _headers(filename: str) -> dict[str, str]:
    return {
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}",
        # 이 주소를 새 탭으로 직접 열어도 문서 안의 스크립트(svg, pdf 등)가
        # 우리 origin 에서 돌지 않게 한다. 미리보기는 바이트만 받아 그린다.
        "Content-Security-Policy": "sandbox",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=86400",
    }


def _media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return (
        _EXTRA_TYPES.get(ext)
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )


def _stored_path(session: Session, attachment_id: int) -> tuple[Attachment, Path]:
    att = session.get(Attachment, attachment_id)
    if att is None or not att.storage_path:
        raise HTTPException(status_code=404, detail="받아 둔 파일이 없다")

    # storage_path 는 DB 값이다. 수집기가 만든 경로라도 첨부 폴더 밖은 내주지 않는다.
    root = settings.attachment_dir.resolve()
    path = Path(att.storage_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="받아 둔 파일이 없다")
    return att, path


@router.get("/{attachment_id}/file")
def get_file(attachment_id: int, session: Session = Depends(get_session)) -> FileResponse:
    """받아 둔 첨부를 내준다. 학교 서버의 다운로드 링크는 다른 origin 이라
    프론트가 바이트를 받아 미리보기를 그릴 수 없다."""
    att, path = _stored_path(session, attachment_id)
    return FileResponse(path, media_type=_media_type(att.filename), headers=_headers(att.filename))


class ZipEntryOut(BaseModel):
    index: int
    name: str
    size: int


def _entry_name(info: zipfile.ZipInfo) -> str:
    # 한국에서 만든 zip 은 대개 UTF-8 플래그 없이 CP949 로 이름을 적는다.
    # 파이썬은 그런 이름을 CP437 로 읽으므로 바이트로 되돌려 다시 푼다.
    if info.flag_bits & _UTF8_FLAG:
        return info.filename
    try:
        raw = info.filename.encode("cp437")
    except UnicodeEncodeError:
        # 유니코드 경로 확장 필드(0x7075)가 있으면 파이썬이 이미 제대로 풀어 둔 이름이다.
        return info.filename
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return info.filename


def _open_zip(path: Path) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="zip 파일을 열 수 없다") from exc


@router.get("/{attachment_id}/entries", response_model=list[ZipEntryOut])
def list_entries(attachment_id: int, session: Session = Depends(get_session)) -> list[ZipEntryOut]:
    """zip 첨부에 든 파일 목록. index 는 아래 entries/{index} 에 그대로 쓴다."""
    _, path = _stored_path(session, attachment_id)
    with _open_zip(path) as z:
        return [
            ZipEntryOut(index=i, name=_entry_name(info), size=info.file_size)
            for i, info in enumerate(z.infolist())
            if not info.is_dir() and not _entry_name(info).startswith("__MACOSX/")
        ]


@router.get("/{attachment_id}/entries/{index}")
def get_entry(attachment_id: int, index: int, session: Session = Depends(get_session)) -> Response:
    _, path = _stored_path(session, attachment_id)
    with _open_zip(path) as z:
        infos = z.infolist()
        if not 0 <= index < len(infos) or infos[index].is_dir():
            raise HTTPException(status_code=404, detail="zip 안에 그런 파일이 없다")
        info = infos[index]
        if info.file_size > MAX_ENTRY_BYTES:
            raise HTTPException(status_code=413, detail="미리 보기에는 너무 큰 파일이다")
        if info.flag_bits & 0x1:
            raise HTTPException(status_code=422, detail="암호가 걸린 파일이다")
        # file_size 는 zip 이 스스로 적은 값이라 믿을 수 없다. 실제로 푼 양도 센다.
        with z.open(info) as f:
            data = f.read(MAX_ENTRY_BYTES + 1)
        if len(data) > MAX_ENTRY_BYTES:
            raise HTTPException(status_code=413, detail="미리 보기에는 너무 큰 파일이다")

    name = _entry_name(info).rsplit("/", 1)[-1]
    return Response(data, media_type=_media_type(name), headers=_headers(name))
