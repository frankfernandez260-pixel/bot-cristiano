from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL

# PostgreSQL en Railway usa "postgres://" pero SQLAlchemy necesita "postgresql://"
_url = DATABASE_URL or ""
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql://", 1)

# connect_args solo aplica a SQLite
_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}

engine = create_engine(_url, connect_args=_connect_args)
SessionLocal = sessionmaker(engine)

def get_session():
    return SessionLocal()
