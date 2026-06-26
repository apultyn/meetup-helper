import os
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    required_names = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing_names = [name for name in required_names if not os.getenv(name)]
    if missing_names:
        missing = ", ".join(missing_names)
        raise RuntimeError(f"Missing required database environment variables: {missing}")

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = quote(os.environ["POSTGRES_USER"], safe="")
    password = quote(os.environ["POSTGRES_PASSWORD"], safe="")
    database = quote(os.environ["POSTGRES_DB"], safe="")

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


DATABASE_URL = build_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
