# KW Notice

광운대학교 공지사항을 매일 모아서 요약하고, 첨부파일 내용까지 검색하게 해 주는 서비스.

## 왜 만드는가

- 학교 AI 챗봇이 첨부파일을 못 읽는다. 정작 중요한 내용은 HWP 안에 있다
- 목록 68건 중 **58건이 상단 고정**이라 새 공지가 파묻힌다
- 목록 정렬 기준이 작성일이 아니라 **수정일**이다. 8월 공지가 어제 공지보다 위에 온다
- 바쁘면 매일 확인하지 못한다

## 구조

```
backend/    FastAPI + PostgreSQL(pgvector). 수집, 추출, 요약, API
frontend/   Vite + React + Tailwind. Gmail 식 3칸 레이아웃
design/     mockup.html (정적 시안)
```

## 띄우기

```bash
# 1. DB
cd backend && docker compose up -d && python -m app.init_db

# 2. 데이터 수집 (처음 한 번)
python -m app.crawler kw_main --pages 2
python -m app.crawler cs_dept --pages 2
python -m app.extract

# 3. API
uvicorn app.api.main:app --reload --port 8000

# 4. 프론트 (다른 터미널)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

요약까지 쓰려면 `backend/.env` 에 `ANTHROPIC_API_KEY` 가 필요하다.

## 매일 돌리기

```bash
cd backend
python -m app.scheduler            # 매일 07:00 (Asia/Seoul)
python -m app.scheduler --now      # 한 번만 즉시
```

수집 → 첨부 추출 → 요약 → 하루치 브리핑을 순서대로 돈다. 각 단계가 앞 단계의
상태를 보고 자기 몫만 집어 가므로, 중간에 실패해도 다음 실행이 이어서 한다.
API 키가 없으면 요약 단계만 건너뛴다.

## API

| | |
| --- | --- |
| `GET /api/notices` | 목록. `source` `category` `pinned` `unread` `starred` `deadline_soon` `q` `sort` |
| `GET /api/notices/{id}` | 본문, 첨부, 이미지 |
| `PUT /api/notices/{id}/read` `​/star` | 읽음, 별표 토글 |
| `GET /api/stats` | 사이드바 집계 |
| `GET /api/sources` | 출처 목록 |
| `GET /api/digests/{date}` | 하루치 브리핑 |

문서는 http://localhost:8000/docs.

`sort` 의 기본값은 `posted`(작성일)다. 학교 사이트와 다른 지점이고, 새 공지가
보이게 만드는 핵심이다.

`q` 는 제목, 본문뿐 아니라 **첨부파일에서 추출한 텍스트까지** 훑는다.
"통장사본" 처럼 본문에 없고 첨부 안에만 있는 말로도 공지가 찾아진다.

## 배포 계획

프론트는 `npm run build` 결과(`dist/`)를 S3 에 올리고 CloudFront 를 붙인다.
CloudFront 에서 `/api/*` 만 백엔드 오리진으로 보내면 브라우저 입장에서 같은
origin 이 되어 CORS 가 사라진다. SPA 라우팅 때문에 404 를 `index.html` 로
돌려주는 custom error response 가 필요하다.

프론트 코드에는 API 주소가 박혀 있지 않다. 개발에서는 Vite proxy 가, 배포에서는
CloudFront 가 같은 일을 한다.

## 자세한 내용

수집 과정에서 알아낸 사이트별 함정, 첨부 추출 방식, 요약 설계는
[backend/README.md](backend/README.md) 에 있다.
