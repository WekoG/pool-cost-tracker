from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .settings import get_settings

settings = get_settings()
connect_args = {'check_same_thread': False} if settings.DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(settings.DATABASE_URL, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
