"""Simple smoke tests that verify the basic functionality works."""
import pickle
from unittest.mock import patch

from sqlite_job.connections import SQLiteJob
from sqlite_job.models import Job, JobStatus, Queue
from sqlite_job.worker import Worker


def test_job_creation(test_session):
    """Test basic job creation works."""
    with test_session() as session:
        # Create queue first
        queue = Queue(name="test_queue")
        session.add(queue)
        session.flush()
        
        # Create job
        job = Job(function="test.function", queue_name="test_queue")
        session.add(job)
        session.flush()
        
        assert job.id is not None
        assert job.status == JobStatus.PENDING


def test_sqlite_job_basic(test_db):
    """Test SQLiteJob basic functionality."""
    with patch('sqlite_job.connections.get_session') as mock_get_session:
        # Use test database session
        from sqlite_job.db import get_session as real_get_session
        
        def mock_session_factory():
            with patch('sqlite_job.db.engine', test_db):
                return real_get_session()
        
        mock_get_session.side_effect = mock_session_factory
        
        job_connection = SQLiteJob("test_queue")
        job_id = job_connection.enqueue("test.function", 1, 2)
        
        assert job_id is not None


def test_worker_creation():
    """Test Worker can be created."""
    worker = Worker("test_queue")
    assert worker.queue_name == "test_queue"


def test_function_serialization():
    """Test function data serialization works."""
    data = {"f": "test.function", "args": (1, 2), "kwargs": {"key": "value"}}
    pickled = pickle.dumps(data)
    unpickled = pickle.loads(pickled)
    
    assert unpickled["f"] == "test.function"
    assert unpickled["args"] == (1, 2)
    assert unpickled["kwargs"] == {"key": "value"}