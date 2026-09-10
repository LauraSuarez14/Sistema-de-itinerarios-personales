"""Engine y factoria de sesiones de SQLAlchemy (sincrono). Un unico engine
compartido por proceso, con `pool_pre_ping` para tolerar reconexiones de
Postgres (util en docker-compose donde el contenedor puede reiniciar)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from ...config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_database_connection() -> bool:
    """Usado por `GET /health`: hace un `SELECT 1` real contra Postgres."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
