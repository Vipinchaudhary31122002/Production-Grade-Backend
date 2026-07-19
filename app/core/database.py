from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from sqlalchemy.pool import QueuePool
from collections.abc import Generator
from app.core.config import settings


class Base(DeclarativeBase):
    pass

engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

def check_database_connection() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection established successfully.")
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        raise RuntimeError(f"Database connection failed: {e}") from e

def dispose_database() -> None:
    engine.dispose()
    print("Database connection pool disposed.")

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()