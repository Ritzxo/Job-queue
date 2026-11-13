import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Read settings from .env (if it exists) into environment variables,
# so the password lives outside the code.
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")

# create_engine does not connect yet; it only connects when a session first uses it.
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass


class JobDB(Base):
    __tablename__ = 'jobs'

    id: Mapped[int] = mapped_column(primary_key=True)
    payload: Mapped[str] 
    status: Mapped[str] = mapped_column(default='pending')
    attempts: Mapped[int] = mapped_column(default=0)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_attempts: Mapped[int] = mapped_column(default=5)
    last_error: Mapped[str | None]


def init_db():
    """Create any missing tables. Run once with `python database.py`, not on import."""
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
    print("Tables created (existing tables are left unchanged).")