"""스키마 생성과 source 시드.

MVP 동안은 Alembic 없이 create_all 로 간다. 스키마가 굳으면 그때
`alembic revision --autogenerate` 로 초기 migration 을 한 번 뜬다.
"""

from sqlalchemy import select, text

from app.db import SessionLocal, engine, ensure_extensions
from app.config import settings
from app.models import Base, Source, User

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


ADDED_COLUMNS = [
    "ALTER TABLE notices ADD COLUMN IF NOT EXISTS image_text TEXT",
    "ALTER TABLE notices ADD COLUMN IF NOT EXISTS image_text_at TIMESTAMPTZ",
]


def main() -> None:
    ensure_extensions()
    Base.metadata.create_all(engine)
    # create_all 은 이미 있는 테이블에 컬럼을 더하지 않는다. Alembic 전까지는 여기서 더한다.
    with engine.begin() as conn:
        for ddl in ADDED_COLUMNS:
            conn.execute(text(ddl))

    with SessionLocal() as session:
        existing = set(session.scalars(select(Source.key)))
        added = [s for s in SEED_SOURCES if s.key not in existing]
        session.add_all(added)
        session.commit()
        # 단일 사용자 MVP. 읽음, 별표를 붙일 주인이 한 명은 있어야 한다.
        user = session.scalar(select(User).where(User.email == settings.default_user_email))
        if user is None:
            session.add(User(email=settings.default_user_email, display_name="me"))
            session.commit()
            seeded_user = settings.default_user_email
        else:
            seeded_user = "이미 있음"

        print(f"tables ready, sources seeded: {[s.key for s in added] or 'none'}")
        print(f"default user: {seeded_user}")


if __name__ == "__main__":
    main()
