from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import datetime, timezone

engine = create_engine('postgresql+psycopg2://jobqueue:jobqueue@localhost:5433/jobqueue')
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

Base.metadata.create_all(engine)