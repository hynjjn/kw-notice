"""HWP 5.x 바이너리(OLE2 Compound File)에서 본문 텍스트를 뽑는다.

`BodyText/SectionN` 스트림은 zlib(raw deflate)으로 압축된 레코드 열이고,
그중 HWPTAG_PARA_TEXT 레코드만 모으면 본문이 된다. 표 안의 셀도 각각
문단 레코드로 들어 있어서 함께 딸려 나온다.
"""

from __future__ import annotations

import struct
import zlib

import olefile

HWPTAG_PARA_TEXT = 16 + 51

# 제어 문자는 세 갈래다. 차지하는 길이가 달라서 구분하지 않으면 본문이 밀린다.
CHAR_CTRL = {0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31}      # 2바이트
EXT_CTRL = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}  # 16바이트
INLINE_CTRL = {4, 5, 6, 7, 8, 9, 19, 20}                      # 16바이트

_LINE_BREAKS = {10, 13}


class Encrypted(ValueError):
    """암호가 걸린 문서. 열 수 없다."""


def _records(buf: bytes):
    i = 0
    while i + 4 <= len(buf):
        (header,) = struct.unpack_from("<I", buf, i)
        i += 4
        tag = header & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:  # 확장 길이는 뒤따르는 4바이트에 들어 있다
            (size,) = struct.unpack_from("<I", buf, i)
            i += 4
        yield tag, buf[i : i + size]
        i += size


def _para_text(payload: bytes) -> str:
    # 코드 유닛을 하나씩 chr() 로 바꾸면 안 된다. 이모지나 확장 한자는
    # UTF-16 surrogate pair 로 들어 있어서, 낱개로 변환하면 짝이 깨진 문자가
    # 남고 나중에 DB 에 넣을 때 UnicodeEncodeError 로 터진다.
    units: list[int] = []
    i = 0
    while i + 2 <= len(payload):
        (code,) = struct.unpack_from("<H", payload, i)
        if code in EXT_CTRL or code in INLINE_CTRL:
            i += 16
            continue
        i += 2
        if code in CHAR_CTRL:
            if code in _LINE_BREAKS:
                units.append(0x0A)
            continue
        units.append(code)

    raw = struct.pack(f"<{len(units)}H", *units)
    return raw.decode("utf-16-le", errors="replace")


def extract(path: str) -> str:
    ole = olefile.OleFileIO(path)
    try:
        (flags,) = struct.unpack("<I", ole.openstream("FileHeader").read()[36:40])
        if flags & 0b10:
            raise Encrypted("암호화된 HWP")
        compressed = bool(flags & 0b1)

        parts: list[str] = []
        for stream in sorted(s for s in ole.listdir() if s[0] == "BodyText"):
            raw = ole.openstream(stream).read()
            data = zlib.decompress(raw, -15) if compressed else raw
            parts += [
                _para_text(payload)
                for tag, payload in _records(data)
                if tag == HWPTAG_PARA_TEXT
            ]
    finally:
        ole.close()

    text = "\n".join(parts)
    return "\n".join(ln.strip() for ln in text.split("\n") if ln.strip())
