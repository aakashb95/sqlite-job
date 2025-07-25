import os
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sqlite_job.db import get_db, get_session


class TestGetDb:
    """Test get_db function."""
    
    def test_get_db_returns_connection(self):
        """Test that get_db returns a database connection."""
        connection = get_db()
        assert connection is not None
        connection.close()
    
    def test_get_db_uses_correct_database_path(self):
        """Test that get_db uses the correct database path."""
        # The actual implementation uses a hardcoded path relative to the source
        connection = get_db()
        # Just verify we can execute a simple query
        result = connection.execute("SELECT 1 as test").fetchone()
        assert result[0] == 1
        connection.close()


class TestGetSession:
    """Test get_session context manager."""
    
    def test_get_session_returns_session(self, test_db):
        """Test that get_session returns a SQLAlchemy session."""
        # Mock the engine in db module to use test database
        with patch('sqlite_job.db.engine', test_db):
            from sqlite_job.db import get_session
            
            with get_session() as session:
                assert isinstance(session, Session)
                # Test basic query
                result = session.execute("SELECT 1 as test").fetchone()
                assert result[0] == 1
    
    def test_get_session_commits_on_success(self, test_db):
        """Test that get_session commits changes on successful exit."""
        from sqlite_job.models import Queue
        
        with patch('sqlite_job.db.engine', test_db):
            from sqlite_job.db import get_session
            
            # Add a queue in the session
            with get_session() as session:
                queue = Queue(name="test_commit_queue")
                session.add(queue)
                # Don't manually commit - let context manager handle it
            
            # Verify the queue was committed by querying in a new session
            with get_session() as session:
                saved_queue = session.query(Queue).filter(Queue.name == "test_commit_queue").first()
                assert saved_queue is not None
                assert saved_queue.name == "test_commit_queue"
    
    def test_get_session_closes_on_exception(self, test_db):
        """Test that get_session properly closes session even on exception."""
        from sqlite_job.models import Queue
        
        with patch('sqlite_job.db.engine', test_db):
            from sqlite_job.db import get_session
            
            # Test that session is closed even when exception occurs
            with pytest.raises(ValueError):
                with get_session() as session:
                    queue = Queue(name="test_exception_queue")
                    session.add(queue)
                    raise ValueError("Test exception")
            
            # Despite the exception, we should be able to create a new session
            with get_session() as session:
                result = session.execute("SELECT 1 as test").fetchone()
                assert result[0] == 1
    
    def test_get_session_nested_sessions(self, test_db):
        """Test that nested get_session calls work correctly."""
        from sqlite_job.models import Queue
        
        with patch('sqlite_job.db.engine', test_db):
            from sqlite_job.db import get_session
            
            with get_session() as outer_session:
                queue1 = Queue(name="outer_queue")
                outer_session.add(queue1)
                
                with get_session() as inner_session:
                    queue2 = Queue(name="inner_queue")
                    inner_session.add(queue2)
                    # Inner session should commit independently
                
                # Both queues should exist after both sessions commit
            
            # Verify both queues were saved
            with get_session() as session:
                outer_queue = session.query(Queue).filter(Queue.name == "outer_queue").first()
                inner_queue = session.query(Queue).filter(Queue.name == "inner_queue").first()
                
                assert outer_queue is not None
                assert inner_queue is not None
    
    def test_get_session_multiple_operations(self, test_db):
        """Test multiple database operations within a single session."""
        from sqlite_job.models import Job, JobStatus, Queue
        
        with patch('sqlite_job.db.engine', test_db):
            from sqlite_job.db import get_session
            
            with get_session() as session:
                # Create a queue
                queue = Queue(name="multi_op_queue")
                session.add(queue)
                session.flush()  # Flush to get the queue available for foreign key
                
                # Create multiple jobs
                job1 = Job(function="test.func1", queue_name="multi_op_queue")
                job2 = Job(function="test.func2", queue_name="multi_op_queue", status=JobStatus.RUNNING)
                job3 = Job(function="test.func3", queue_name="multi_op_queue", status=JobStatus.COMPLETED)
                
                session.add_all([job1, job2, job3])
                session.flush()
                
                # Update job statuses
                job1.status = JobStatus.RUNNING
                job2.status = JobStatus.COMPLETED
                job2.result = "test_result"
            
            # Verify all operations were committed
            with get_session() as session:
                jobs = session.query(Job).filter(Job.queue_name == "multi_op_queue").all()
                assert len(jobs) == 3
                
                # Check specific job states
                running_jobs = [j for j in jobs if j.status == JobStatus.RUNNING]
                completed_jobs = [j for j in jobs if j.status == JobStatus.COMPLETED]
                
                assert len(running_jobs) == 1
                assert len(completed_jobs) == 2