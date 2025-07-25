from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("sqlite:///sqlite_job.db")


def get_db():
    return engine.connect()


@contextmanager
def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.commit()
        session.close()
