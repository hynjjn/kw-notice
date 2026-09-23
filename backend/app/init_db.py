"""스키마 생성과 source 시드.

MVP 동안은 Alembic 없이 create_all 로 간다. 스키마가 굳으면 그때
`alembic revision --autogenerate` 로 초기 migration 을 한 번 뜬다.
"""

from sqlalchemy import select

from app.db import SessionLocal, engine, ensure_extensions
from app.models import Base, Source

SEED_SOURCES = [
    Source(
        key="kw_main",
        name="광운대학교 공지사항",
        list_url="https://www.kw.ac.kr/ko/life/notice.jsp"
        "?srCategoryId=&mode=list&searchKey=1&searchVal=",
        parser="kw_main",
    ),
    Source(
        key="cs_dept",
        name="소프트웨어학부 공지사항",
        list_url="https://cs.kw.ac.kr/department_office/lecture.php",
        parser="cs_dept",
    ),
]


def main() -> None:
    ensure_extensions()
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        existing = set(session.scalars(select(Source.key)))
        added = [s for s in SEED_SOURCES if s.key not in existing]
        session.add_all(added)
        session.commit()
        print(f"tables ready, sources seeded: {[s.key for s in added] or 'none'}")


if __name__ == "__main__":
    main()
