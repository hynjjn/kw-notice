# KW Notice backend

FastAPI + PostgreSQL(pgvector). 광운대학교 공지사항과 소프트웨어학부 공지를
매일 크롤링해서 요약하고, 첨부파일까지 읽어 질문에 답한다.

## 로컬 실행

```bash
docker compose up -d                 # Postgres 16 + pgvector, 5433 포트
cp .env.example .env
uv sync                              # 또는 pip install -e .
python -m app.init_db                # 테이블 생성 + source 시드
```

5432가 아니라 **5433**을 쓴다. 로컬에 이미 돌고 있는 Postgres와 부딪히지 않게 하려는 것.

## 스키마 결정

앞서 열어 두었던 세 가지를 이렇게 정했다.

### 1. 중복 판정 키는 `(source_id, external_id)`

`external_id`는 목록에 보이는 번호가 아니라 **상세 URL의 고유 ID**다.
대학 공지는 `DUID`, 소프트웨어학부는 `no` 파라미터를 쓴다.

학부 게시판은 표시 번호(77)와 URL의 `no`(3417)가 다르다. 표시 번호를 키로 쓰면
글이 하나 지워지는 순간 모든 번호가 한 칸씩 밀려서, 이미 읽은 공지가 전부
새 공지로 둔갑한다.

### 2. 본문 변경은 `content_hash`로 감지한다

`normalize(body_text)`의 sha256을 들고 있다가, 값이 달라지면 `content_revision`을
올리고 `content_changed_at`을 찍는다. 그러면 세 가지가 따라온다.

- 목록에 "변경됨" 배지를 띄울 수 있다. 마감일이 조용히 연장되는 공지가 꽤 있다
- 요약을 다시 만들 대상을 정확히 고를 수 있다
- RAG 청크를 어느 개정 기준으로 만들었는지 `notice_chunks.content_revision`으로 추적된다

이력 테이블(`notice_revisions`)은 만들지 않았다. MVP에서 과거 본문을 보여줄 화면이 없다.

### 3. `is_pinned`는 현재 상태만, 이력은 없다

고정 여부는 **목록에서의 행 순서가 날짜 정렬 순서와 어긋나는지**로 판정한다.
사이트가 고정 공지에 별도 마크업을 주지 않기 때문이다. `pinned_rank`로 고정
공지끼리의 순서를 유지한다.

## 테이블

| 테이블 | 역할 |
| --- | --- |
| `sources` | 크롤링 대상 게시판. 학부 게시판 추가는 행 추가로 끝난다 |
| `notices` | 공지 본문, 수집 메타, AI 요약, 전문 검색용 `tsv` |
| `attachments` | 첨부 파일과 추출된 텍스트. `extract_state`로 파싱 성공 여부 추적 |
| `users` / `user_notice_state` | 읽음, 별표, 알림 끄기 |
| `daily_digests` | 하루치 요약. `user_id`가 null이면 공용 |
| `notice_chunks` | RAG 청크 + 임베딩(1024차원) |
| `crawl_runs` | 크롤 실행 로그. 조용한 실패를 잡는 용도 |

## 보류한 것

- **Alembic**: 스키마가 흔들리는 동안은 `create_all`이 빠르다. 크롤러가 돌기 시작하면 도입한다
- **벡터 인덱스 생성**: HNSW 인덱스 정의는 `models.py`에 있지만, 행이 쌓인 뒤 만드는 게 맞다. 비어 있는 테이블에 만들면 품질이 나쁘다
- **한국어 전문 검색**: `to_tsvector('simple', ...)`로 시작한다. 아쉬워지면 `pg_bigm`을 얹는다

## 크롤러

```bash
python -m app.crawler kw_main                       # 1페이지, 상세 + 첨부까지
python -m app.crawler kw_main --pages 3             # 3페이지
python -m app.crawler kw_main --limit 5 --no-download   # 테스트용
```

멱등하다. 같은 실행을 반복해도 신규 0, 상세수집 0으로 끝난다.

### 사이트에서 확인한 것

**고정 공지는 `li.top-notice` 로 명시된다.** 행 순서로 추론할 필요가 없었다.
다만 그 수가 **68건 중 58건**이다. 고정이 아닌 새 공지는 페이지당 10건뿐이고,
나머지는 전부 상단에 눌러앉아 있다. 이 서비스를 만드는 이유가 그대로 데이터로 나온다.

**목록 정렬 기준은 작성일이 아니라 수정일이다.** 8월 20일에 올라온 공지가
9월 16일에 수정되면 9월 21일 공지보다 위에 온다. 그래서 `posted_at` 으로 다시
정렬해야 "오늘 올라온 것"이 제대로 보인다. `content_hash` 로 실제 본문 변경을
가려내는 장치가 필요한 이유이기도 하다. 수정일만 올라가고 내용은 그대로인 경우가 흔하다.

**본문이 포스터 이미지뿐인 공지가 23%다.** 78건 중 18건에 `body_text` 가 없었고,
그 18건 전부가 `<img>` 만 들고 있었다. 이건 요약 단계에서 vision 이 필요하다는
뜻이라 `notices.inline_image_urls` 에 이미지 URL 을 담아 둔다.

**첨부의 신원은 URL(`Download.jsp?fuid=...`)이다.** sha256 은 실제로 내려받아야
알 수 있어서 식별 키로 못 쓴다. `--no-download` 실행과 섞이면 같은 파일이 두 번 들어간다.

### 수집 결과 (2페이지 기준)

| | |
| --- | --- |
| 공지 | 78건, 상세 파싱 실패 0 |
| 첨부 | 75건 / hwp 29, pdf 29, hwpx 4, 나머지 doc·xlsx·zip·이미지 |
| 소요 | 약 42초 (요청 간 0.4초 간격 포함) |

**hwp 계열이 33건으로 가장 많다.** 3단계 rhwp 검증의 표본은 `var/attachments/` 에 이미 있다.

## 첨부 텍스트 추출

```bash
python -m app.extract                    # extract_state 가 pending 인 것만
python -m app.extract --ext hwp hwpx     # 확장자 한정
python -m app.crawler.backfill --ext pdf # 아직 안 받은 첨부 채우기
```

### rhwp 는 쓰지 않는다

HWP 텍스트 추출에 [rhwp](https://github.com/edwardkim/rhwp) 를 쓰려고 릴리스
바이너리까지 받아 SHA256 을 맞췄지만(`7d8928fa…`), 그 전에 잰 순수 Python
기준선이 충분히 좋았다.

| 포맷 | 건수 | 결과 | 방법 |
| --- | --- | --- | --- |
| hwp (HWP 5.x 바이너리) | 28 | **28 성공** | olefile + zlib + 레코드 파싱 |
| hwpx | 4 | **4 성공** | 표준 라이브러리 zipfile + ElementTree |
| pdf | 24 | 22 성공 | pymupdf |

hwp 평균 4,165자에 표 셀과 체크박스까지 그대로 나온다. rhwp 는 렌더링
(HWP → IR → SVG → PDF)이 강점이라, 남는 용도는 **첨부 미리보기**다.
프론트 작업에 들어갈 때 다시 본다.

실패한 pdf 2건은 포스터라 텍스트 레이어가 아예 없다. 본문이 이미지뿐인 공지와
같은 부류이므로 4단계에서 vision 으로 함께 처리한다.

### 주의: UTF-16 surrogate pair

HWP 본문은 UTF-16LE 코드 유닛 열이다. `chr(code)` 로 낱개 변환하면 이모지나
확장 한자의 surrogate pair 가 깨져서, DB 에 넣는 순간
`UnicodeEncodeError: surrogates not allowed` 로 터진다. 코드 유닛을 모아
한 번에 `decode("utf-16-le")` 해야 한다.

## 출처별 요청 간격

`kw_main` 은 0.4초, `cs_dept` 는 2.5초다. 각 파서 모듈의 `REQUEST_DELAY` 에 있다.

본교 서버(Tomcat)는 0.4초로 78건을 연속 수집해도 멀쩡했지만, 학부 서버는
**openresty 리버스 프록시**를 앞에 두고 있고 훨씬 예민하다. 0.4초로 44요청
(목록 2 + 상세 20 + 첨부 22)을 20초 남짓에 쏘자 **IP 단위로 10분 넘게 403** 을 맞았다.
사이트 전체가 막혀서 `robots.txt` 조차 403 이었다. 참고로 `www.kw.ac.kr` 의
robots.txt 는 `User-agent: * / Allow: /` 이고, `cs.kw.ac.kr` 에는 robots.txt 가 없다(404).

그래서 403 이나 429 를 만나면 재시도하지 않고 **그 출처의 실행을 즉시 중단**한다
(`http.Blocked`). 이미 막힌 상태에서 남은 요청을 계속 두드리면 차단 시간만 늘어난다.
`Retry-After` 가 30초를 넘어도 같은 판단을 한다. 사용자가 버튼을 눌러 가끔 도는
작업이라 속도는 의미가 없다.

## 다운로드한 첨부는 내용을 검사한다

학부 게시판은 없는 파일을 요청해도 404 를 주지 않는다. **200 에 75바이트 HTML** 을 싣는다.

```html
<script> alert('없는파일입니다.2'); history.go(-1); </script>
```

확장자만 믿고 저장하면 `.pdf` 인 HTML 이 디스크에 쌓이고, 한참 뒤 추출 단계에서
엉뚱한 자리로 터진다. `crawler/filetype.py` 가 받는 자리에서 magic byte 를 보고
거른다. 걸린 첨부는 파일을 저장하지 않고 `extract_state=failed` 로 사유를 남긴다.

## 소프트웨어학부 게시판에서 확인한 것

**고정 공지 개념이 없다.** 제목 앞에 붙은 "공지", "[공지]" 는 작성자가 직접
타이핑한 글자라 마크업이 아니다. `is_pinned` 는 항상 false 다.

**표시 번호와 URL 의 `no` 가 다르다.** 목록에 77 로 보이는 글의 상세 URL 은
`no=3417` 이다. 1단계에서 external_id 를 표시 번호로 잡지 않은 이유가 이거다.

**본문 포스터를 base64 로 박아 넣는다.** `<img src=data:image/png;base64,...>` 인데
따옴표가 없다. HTML 파서가 값을 속성으로 쪼개면서 base64 한 덩어리가 100자짜리
조각 **19만 3천 개의 속성 이름** 으로 흩어지고, `src` 값은 빈 문자열이 된다.
그래서 `src` 가 `data:` 로 시작하는지 보는 것만으로는 안 걸린다. 속성 개수로 잡는다
(`_MAX_ATTRS = 50`). 상세 페이지 하나가 11.5MB 인데 걷어내면 22KB 가 된다.
같은 이미지가 첨부로도 올라오므로 버려도 잃는 게 없다.

## 검증 결과

```
출처       공지  파싱  실패  고정  본문없음
cs_dept     20    20     0     0      1
kw_main     78    78     0    58     18

첨부  ok 72 / unsupported 15 / pending 14 / failed 2
      failed 2건은 "응답이 75바이트뿐" — 디스크에 저장되지 않음
      디스크 실제 파일 87개 = ok 72 + unsupported 15
```

- 두 출처 모두 상세 파싱 실패 0
- 재실행 시 신규 0, 상세수집 0 (멱등)
- `cs_dept` 를 2.5초 간격으로 재수집했을 때 403 없이 완주
- 이전에 403 이던 `no=3022` 도 정상 수집됨. 개별 글 권한 문제가 아니라
  IP 차단에 휩쓸린 것이었다
- `content_hash` 가 실전에서 동작: 공지 `53369` 가 작성일 09-18, 수정일 09-23 으로
  본문이 실제로 바뀌어 `content_revision` 이 2 로 올라갔다

## AI 요약

```bash
# 평소에는 프론트의 "AI 요약 만들기" 버튼이 한 건씩 요약한다. 아래는 수동 일괄용이다.
python -m app.summarize --dry-run          # API 호출 없이 대상과 분량만 확인
python -m app.summarize --limit 5          # 5건만
python -m app.summarize                    # 요약이 없거나 본문이 바뀐 것 전부
python -m app.summarize --digest 2026-09-23   # 그날의 하루치 요약
```

`GEMINI_API_KEY` 가 `.env` 에 있어야 한다. 모델은 `GEMINI_MODEL` 로 바꾼다
(기본값 `gemini-3.8-flash`).

### 설계

**모델은 Gemini Flash, thinking level 은 `low`.** 요약은 판단이 복잡한 일이 아니라
읽고 추리는 일이다. 생각을 짧게 시켜도 품질이 떨어지지 않으면서 토큰이 줄어든다.
호출은 `app/summarize/llm.py` 한곳에 모았다.

**system 프롬프트에는 변동값을 넣지 않는다.** Gemini 의 암묵적 캐시는 prefix
일치라 앞머리가 한 바이트라도 바뀌면 깨진다. `prompt.SYSTEM` 에는 날짜나 공지별
값이 들어가지 않는다. 공지마다 달라지는 내용은 전부 user 메시지에 있다.

**출력은 구조화한다.** `response_schema=NoticeSummary` 로
`bullets` 와 `deadline` 을 받는다. 마감일이 따로 나와야 "마감 임박한 것만"
필터를 만들 수 있다. 자유 텍스트에서 날짜를 다시 긁는 것보다 정확하다.

**본문이 이미지뿐인 공지는 그림을 함께 보낸다.** `inline_image_urls` 를
직접 내려받아 이미지 Part 로 최대 5장까지 싣는다. 학교 챗봇이 못 하는 부분이다.

**하루치 요약은 원문을 다시 읽지 않는다.** 개별 요약이 이미 있으므로 그것만
모아서 브리핑한다. 같은 날 공지 20건을 원문으로 다시 넣는 것보다 훨씬 싸다.

### 입력 규모 (측정값)

```
대상 98건 / 본문+첨부 297,487자 / 이미지 31장
입력 토큰 대략 208,240 (문자 수 기반 추정, 실측 아님)
```

한 건에 실어 보내는 양은 본문 12,000자, 첨부 하나당 8,000자, 합계 40,000자로
자른다(`prompt.py`). 가장 긴 첨부가 27,000자였는데 그걸 통째로 넣을 이유가 없다.

### 재요약 조건

`ai_summarized_at < content_changed_at` 인 공지만 다시 요약한다. 크롤러가
`content_hash` 로 본문 변경을 잡아 주므로, 수정일만 올라간 공지는 요약을
다시 만들지 않는다.
