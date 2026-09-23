"""HWPX(Open XML) 텍스트 추출. zip + XML 이라 표준 라이브러리로 끝난다."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile

_SECTION = re.compile(r"Contents/section\d+\.xml", re.IGNORECASE)
# 문단 끝을 줄바꿈으로 살리려면 p 와 t 를 함께 봐야 한다.
_PARA_TAG = "}p"
_TEXT_TAG = "}t"


def extract(path: str) -> str:
    lines: list[str] = []
    with zipfile.ZipFile(path) as z:
        for name in sorted(n for n in z.namelist() if _SECTION.fullmatch(n)):
            root = ET.fromstring(z.read(name))
            for para in root.iter():
                if not para.tag.endswith(_PARA_TAG):
                    continue
                chunk = "".join(
                    t.text for t in para.iter() if t.tag.endswith(_TEXT_TAG) and t.text
                )
                if chunk.strip():
                    lines.append(chunk.strip())
    return "\n".join(lines)
