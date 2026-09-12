from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()
url = settings.sqlalchemy_url

if url.startswith("sqlite"):
    # Dev local: SQLite. check_same_thread=False porque FastAPI usa threadpool.
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # Serverless (Vercel) contra el pooler de Supabase (pgbouncer transaction-mode):
    # NullPool — cada request abre/cierra; el pooling real lo hace pgbouncer.
    engine = create_engine(url, poolclass=NullPool)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
