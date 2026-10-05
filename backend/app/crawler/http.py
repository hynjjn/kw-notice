from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)

# Retry-After 가 이보다 길면 이번 실행은 포기한다. 나중에 다시 가져오면 된다.
MAX_RETRY_AFTER = 30.0


class Blocked(RuntimeError):
    """출처가 우리를 막았다. 이 실행에서 더 두드리면 차단만 길어진다."""


class Fetch(RuntimeError):
    """한 URL 을 못 받았다. 나머지는 계속 진행해도 된다."""


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"},
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
    )


@dataclass
class Fetcher:
    """출처별 요청 간격을 들고 다니는 얇은 래퍼.

    간격을 전역 상수로 두면 서버마다 다른 인내심을 맞출 수 없다.
    본교 서버는 0.4초에도 78건을 버텼지만, openresty 앞단을 쓰는 학부 서버는
    0.4초로 44요청을 쏘자 IP 단위로 10분 넘게 막았다.
    """

    client: httpx.Client
    delay: float
    retries: int = 2

    def get(self, url: str) -> httpx.Response:
        last: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                res = self.client.get(url)
                res.raise_for_status()
                time.sleep(self.delay)
                return res
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                if code in (403, 429):
                    raise Blocked(f"HTTP {code}: {url}") from exc
                if 400 <= code < 500:
                    # 404 같은 건 다시 물어도 같은 답이다.
                    raise Fetch(f"HTTP {code}: {url}") from exc
                last = exc
                wait = _retry_after(exc.response)
            except Exception as exc:  # noqa: BLE001 - 네트워크 예외는 재시도한다
                last = exc
                wait = None

            if attempt < self.retries:
                time.sleep(wait if wait is not None else 1.5 * (attempt + 1))

        raise Fetch(f"GET 실패: {url}") from last


def _retry_after(res: httpx.Response) -> float | None:
    raw = res.headers.get("Retry-After")
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        return None  # HTTP-date 형식은 다루지 않는다
    if seconds > MAX_RETRY_AFTER:
        raise Blocked(f"Retry-After {seconds:.0f}초. 이번 실행은 접는다")
    return seconds
