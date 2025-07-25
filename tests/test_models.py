import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from sqlite_job.models import Job, JobStatus, Queue


class TestJobStatus:
    """Test JobStatus enum."""
    
    def test_job_status_values(self):
        """Test that JobStatus has correct enum values."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"


class TestQueue:
    """Test Queue model."""
    
    def test_create_queue(self, test_session):
        """Test creating a queue."""
        with test_session() as session:
            queue = Queue(name="test_queue")
            session.add(queue)
            session.flush()
            
            assert queue.name == "test_queue"
            assert isinstance(queue.created_at, datetime)
            assert isinstance(queue.updated_at, datetime)
    
    def test_queue_primary_key(self, test_session):
        """Test that queue name is the primary key."""
        with test_session() as session:
            queue = Queue(name="unique_queue")
            session.add(queue)
            session.flush()
            
            # Try to create another queue with same name (should fail)
            with pytest.raises(Exception):  # IntegrityError
                duplicate_queue = Queue(name="unique_queue")
                session.add(duplicate_queue)
                session.flush()


class TestJob:
    """Test Job model."""
    
    def test_create_job_with_defaults(self, test_session):
        """Test creating a job with default values."""
        with test_session() as session:
            # First create a queue
            queue = Queue(name="test_queue")
            session.add(queue)
            session.flush()
            
            job = Job(
                function="test.function",
                queue_name="test_queue"
            )
            session.add(job)
            session.flush()
            
            assert isinstance(job.id, str)
            assert len(job.id) == 36  # UUID4 length
            assert job.function == "test.function"
            assert job.result is None
            assert job.status == JobStatus.PENDING
            assert job.queue_name == "test_queue"
            assert isinstance(job.created_at, datetime)
            assert isinstance(job.updated_at, datetime)
    
    def test_create_job_with_custom_values(self, test_session):
        """Test creating a job with custom values."""
        custom_id = str(uuid.uuid4())
        
        with test_session() as session:
            # First create a queue
            queue = Queue(name="custom_queue")
            session.add(queue)
            session.flush()
            
            job = Job(
                id=custom_id,
                function="custom.function",
                result="test_result",
                status=JobStatus.COMPLETED,
                queue_name="custom_queue"
            )
            session.add(job)
            session.flush()
            
            assert job.id == custom_id
            assert job.function == "custom.function"
            assert job.result == "test_result"
            assert job.status == JobStatus.COMPLETED
            assert job.queue_name == "custom_queue"
    
    def test_job_status_update(self, test_session):
        """Test updating job status."""
        with test_session() as session:
            # Create queue and job
            queue = Queue(name="status_test_queue")
            session.add(queue)
            session.flush()
            
            job = Job(
                function="test.function",
                queue_name="status_test_queue"
            )
            session.add(job)
            session.flush()
            
            # Update status
            job.status = JobStatus.RUNNING
            session.flush()
            
            assert job.status == JobStatus.RUNNING
            
            # Update to completed
            job.status = JobStatus.COMPLETED
            job.result = "finished"
            session.flush()
            
            assert job.status == JobStatus.COMPLETED
            assert job.result == "finished"
    
    def test_job_foreign_key_constraint(self, test_session):
        """Test that job requires valid queue_name."""
        with test_session() as session:
            # Try to create job without queue (should fail with foreign key constraint)
            job = Job(
                function="test.function",
                queue_name="nonexistent_queue"
            )
            session.add(job)
            
            with pytest.raises(Exception):  # IntegrityError
                session.flush()
    
    def test_multiple_jobs_same_queue(self, test_session):
        """Test creating multiple jobs in the same queue."""
        with test_session() as session:
            # Create queue
            queue = Queue(name="multi_job_queue")
            session.add(queue)
            session.flush()
            
            # Create multiple jobs
            job1 = Job(function="test.function1", queue_name="multi_job_queue")
            job2 = Job(function="test.function2", queue_name="multi_job_queue")
            job3 = Job(function="test.function3", queue_name="multi_job_queue")
            
            session.add_all([job1, job2, job3])
            session.flush()
            
            # Verify all jobs were created
            jobs = session.query(Job).filter(Job.queue_name == "multi_job_queue").all()
            assert len(jobs) == 3
            
            # Verify they have different IDs
            job_ids = [job.id for job in jobs]
            assert len(set(job_ids)) == 3  # All unique