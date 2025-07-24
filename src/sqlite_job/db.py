from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import os
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sqlite_job.db")
engine = create_engine(f"sqlite:///{db_path}")


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
