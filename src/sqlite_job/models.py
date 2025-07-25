import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import declarative_base

from sqlite_job.db import get_engine

Base = declarative_base()


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    function = Column(Text)
    result = Column(Text)
    status = Column(String, default=JobStatus.PENDING)
    queue_name = Column(String, ForeignKey("queues.name"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Queue(Base):
    __tablename__ = "queues"

    name = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


def create_tables(database_path: str):
    """Create tables for the specified database."""
    engine = get_engine(database_path)
    Base.metadata.create_all(engine)
