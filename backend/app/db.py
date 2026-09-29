import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()  # Load .env
load_dotenv(".env.local", override=True)  # Load .env.local with override


def _build_database_url():
    """Use DATABASE_URL when set, otherwise assemble it from POSTGRES_* vars.

    URL.create escapes special characters (e.g. '@' or '/') in the password,
    which plain string formatting would not.
    """
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url
    return URL.create(
        "postgresql",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB"),
    )


DATABASE_URL = _build_database_url()

_connect_args = {}
if str(DATABASE_URL).startswith("sqlite"):
    # SQLite (used in tests) is accessed from FastAPI's threadpool.
    _connect_args["check_same_thread"] = False

Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
