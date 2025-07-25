from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Cache engines by database path to avoid recreating them
_engines = {}
_tables_created = set()

def get_engine(database_path: str):
    """Get or create an engine for the specified database path."""
    if database_path not in _engines:
        _engines[database_path] = create_engine(f"sqlite:///{database_path}")
    return _engines[database_path]


def get_db(database_path: str):
    return get_engine(database_path).connect()


@contextmanager
def get_session(database_path: str):
    # Ensure tables are created for this database
    if database_path not in _tables_created:
        from sqlite_job.models import create_tables
        create_tables(database_path)
        _tables_created.add(database_path)
    
    engine = get_engine(database_path)
    session = Session(engine)
    try:
        yield session
    finally:
        session.commit()
        session.close()
