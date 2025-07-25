import pickle
import threading
import time
from unittest.mock import patch

import pytest

from sqlite_job.connections import SQLiteJob
from sqlite_job.models import Job, JobStatus, Queue
from sqlite_job.worker import Worker


class TestIntegration:
    """Integration tests for the full job workflow."""
    
    def test_simple_function_execution_with_mock_import(self, test_db):
        """Test complete workflow from enqueue to execution with mocked imports."""
        # Mock the import system to provide our test functions
        def mock_simple_add(a, b):
            return a + b
        
        # Patch all the database components to use test database
        with patch('sqlite_job.models.engine', test_db), \
             patch('sqlite_job.db.engine', test_db), \
             patch('sqlite_job.connections.get_session') as mock_get_session, \
             patch('sqlite_job.worker.get_session') as mock_worker_get_session:
            
            # Setup session mocking for both modules
            from sqlite_job.db import get_session as real_get_session
            
            def mock_session_factory():
                return real_get_session()
            
            mock_get_session.side_effect = mock_session_factory
            mock_worker_get_session.side_effect = mock_session_factory
            
            # Create SQLiteJob and enqueue a job
            job_connection = SQLiteJob("integration_queue")
            job_id = job_connection.enqueue("test.simple_add", 5, 7)
            
            assert job_id is not None
            
            # Verify job was created in database
            with real_get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                assert job is not None
                assert job.status == JobStatus.PENDING
                assert job.queue_name == "integration_queue"
                
                # Verify queue was created
                queue = session.query(Queue).filter(Queue.name == "integration_queue").first()
                assert queue is not None
            
            # Create worker and process the job
            worker = Worker("integration_queue")
            
            # Mock the import for job execution
            with patch('sqlite_job.connections.importlib.import_module') as mock_import:
                mock_module = type('MockModule', (), {'simple_add': mock_simple_add})()
                mock_import.return_value = mock_module
                
                # Process one job
                job_id_from_worker = worker._get_job_id()
                assert job_id_from_worker == job_id
                
                worker._process_job(job_id)
            
            # Verify job was completed
            with real_get_session() as session:
                completed_job = session.query(Job).filter(Job.id == job_id).first()
                assert completed_job.status == JobStatus.COMPLETED
                
                # Verify result
                result = pickle.loads(completed_job.result)
                assert result == 12  # 5 + 7
            
            # Test getting result through job_connection
            with patch('sqlite_job.connections.importlib.import_module'):
                job_result = job_connection.get_job_result(job_id)
                unpickled_result = pickle.loads(job_result)
                assert unpickled_result == 12
    
    def test_multiple_jobs_processing_with_mock_import(self, test_db):
        """Test processing multiple jobs in sequence."""
        def mock_multiply(x, y):
            return x * y
        
        def mock_add(a, b):
            return a + b
        
        with patch('sqlite_job.models.engine', test_db), \
             patch('sqlite_job.db.engine', test_db), \
             patch('sqlite_job.connections.get_session') as mock_get_session, \
             patch('sqlite_job.worker.get_session') as mock_worker_get_session:
            
            from sqlite_job.db import get_session as real_get_session
            
            def mock_session_factory():
                return real_get_session()
            
            mock_get_session.side_effect = mock_session_factory
            mock_worker_get_session.side_effect = mock_session_factory
            
            # Enqueue multiple jobs
            job_connection = SQLiteJob("multi_job_queue")
            
            job_id1 = job_connection.enqueue("test.multiply", 3, 4)
            job_id2 = job_connection.enqueue("test.add", 10, 20)
            job_id3 = job_connection.enqueue("test.multiply", 5, 6)
            
            # Verify all jobs are pending
            with real_get_session() as session:
                pending_jobs = session.query(Job).filter(
                    Job.queue_name == "multi_job_queue",
                    Job.status == JobStatus.PENDING
                ).all()
                assert len(pending_jobs) == 3
            
            # Create worker
            worker = Worker("multi_job_queue")
            
            # Mock imports for different functions
            def mock_import_side_effect(module_name):
                if module_name == "test":
                    return type('MockModule', (), {
                        'multiply': mock_multiply,
                        'add': mock_add
                    })()
                raise ImportError(f"No module named {module_name}")
            
            with patch('sqlite_job.connections.importlib.import_module', side_effect=mock_import_side_effect):
                # Process all jobs
                processed_jobs = []
                for _ in range(3):
                    job_id = worker._get_job_id()
                    if job_id:
                        worker._process_job(job_id)
                        processed_jobs.append(job_id)
                
                assert len(processed_jobs) == 3
            
            # Verify all jobs completed with correct results
            with real_get_session() as session:
                completed_jobs = session.query(Job).filter(
                    Job.queue_name == "multi_job_queue",
                    Job.status == JobStatus.COMPLETED
                ).all()
                assert len(completed_jobs) == 3
                
                # Check specific results
                for job in completed_jobs:
                    result = pickle.loads(job.result)
                    if job.id == job_id1:
                        assert result == 12  # 3 * 4
                    elif job.id == job_id2:
                        assert result == 30  # 10 + 20
                    elif job.id == job_id3:
                        assert result == 30  # 5 * 6
    
    def test_job_with_kwargs_integration(self, test_db):
        """Test job execution with keyword arguments."""
        def mock_complex_function(a, b=10, c=20, multiplier=1):
            return (a + b + c) * multiplier
        
        with patch('sqlite_job.models.engine', test_db), \
             patch('sqlite_job.db.engine', test_db), \
             patch('sqlite_job.connections.get_session') as mock_get_session, \
             patch('sqlite_job.worker.get_session') as mock_worker_get_session:
            
            from sqlite_job.db import get_session as real_get_session
            
            def mock_session_factory():
                return real_get_session()
            
            mock_get_session.side_effect = mock_session_factory
            mock_worker_get_session.side_effect = mock_session_factory
            
            # Enqueue job with kwargs
            job_connection = SQLiteJob("kwargs_queue")
            job_id = job_connection.enqueue(
                "test.complex_function", 
                5,  # a
                b=15,  # override default b=10
                multiplier=3  # custom kwarg
                # c will use default value of 20
            )
            
            # Process the job
            worker = Worker("kwargs_queue")
            
            with patch('sqlite_job.connections.importlib.import_module') as mock_import:
                mock_module = type('MockModule', (), {'complex_function': mock_complex_function})()
                mock_import.return_value = mock_module
                
                worker._process_job(job_id)
            
            # Verify result: (5 + 15 + 20) * 3 = 120
            with real_get_session() as session:
                completed_job = session.query(Job).filter(Job.id == job_id).first()
                assert completed_job.status == JobStatus.COMPLETED
                
                result = pickle.loads(completed_job.result)
                assert result == 120
    
    def test_empty_queue_handling(self, test_db):
        """Test worker behavior with empty queue."""
        with patch('sqlite_job.models.engine', test_db), \
             patch('sqlite_job.db.engine', test_db), \
             patch('sqlite_job.connections.get_session') as mock_get_session, \
             patch('sqlite_job.worker.get_session') as mock_worker_get_session:
            
            from sqlite_job.db import get_session as real_get_session
            
            def mock_session_factory():
                return real_get_session()
            
            mock_get_session.side_effect = mock_session_factory
            mock_worker_get_session.side_effect = mock_session_factory
            
            # Create worker for empty queue
            worker = Worker("empty_queue")
            
            # Try to get job from empty queue
            job_id = worker._get_job_id()
            assert job_id is None
    
    def test_different_queues_isolation(self, test_db):
        """Test that workers only process jobs from their assigned queue."""
        def mock_function(value):
            return value * 2
        
        with patch('sqlite_job.models.engine', test_db), \
             patch('sqlite_job.db.engine', test_db), \
             patch('sqlite_job.connections.get_session') as mock_get_session, \
             patch('sqlite_job.worker.get_session') as mock_worker_get_session:
            
            from sqlite_job.db import get_session as real_get_session
            
            def mock_session_factory():
                return real_get_session()
            
            mock_get_session.side_effect = mock_session_factory
            mock_worker_get_session.side_effect = mock_session_factory
            
            # Create jobs in different queues
            job_connection_a = SQLiteJob("queue_a")
            job_connection_b = SQLiteJob("queue_b")
            
            job_id_a = job_connection_a.enqueue("test.function", 5)
            job_id_b = job_connection_b.enqueue("test.function", 10)
            
            # Create worker for queue_a only
            worker_a = Worker("queue_a")
            
            with patch('sqlite_job.connections.importlib.import_module') as mock_import:
                mock_module = type('MockModule', (), {'function': mock_function})()
                mock_import.return_value = mock_module
                
                # Worker A should only get job from queue A
                job_id = worker_a._get_job_id()
                assert job_id == job_id_a
                
                worker_a._process_job(job_id)
                
                # Try to get another job - should be None since queue B job shouldn't be visible
                job_id = worker_a._get_job_id()
                assert job_id is None
            
            # Verify only queue A job was processed
            with real_get_session() as session:
                job_a = session.query(Job).filter(Job.id == job_id_a).first()
                job_b = session.query(Job).filter(Job.id == job_id_b).first()
                
                assert job_a.status == JobStatus.COMPLETED
                assert job_b.status == JobStatus.PENDING  # Still pending
                
                result_a = pickle.loads(job_a.result)
                assert result_a == 10  # 5 * 2
    
    def test_job_status_transitions(self, test_db):
        """Test that job status transitions correctly through the workflow."""
        def mock_slow_function(duration):
            time.sleep(0.01)  # Small delay to simulate work
            return f"completed after {duration}"
        
        with patch('sqlite_job.models.engine', test_db), \
             patch('sqlite_job.db.engine', test_db), \
             patch('sqlite_job.connections.get_session') as mock_get_session, \
             patch('sqlite_job.worker.get_session') as mock_worker_get_session:
            
            from sqlite_job.db import get_session as real_get_session
            
            def mock_session_factory():
                return real_get_session()
            
            mock_get_session.side_effect = mock_session_factory
            mock_worker_get_session.side_effect = mock_session_factory
            
            # Enqueue job
            job_connection = SQLiteJob("status_queue")
            job_id = job_connection.enqueue("test.slow_function", 0.01)
            
            # Verify initial status
            with real_get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                assert job.status == JobStatus.PENDING
                assert job.result is None
            
            # Process job
            worker = Worker("status_queue")
            
            with patch('sqlite_job.connections.importlib.import_module') as mock_import:
                mock_module = type('MockModule', (), {'slow_function': mock_slow_function})()
                mock_import.return_value = mock_module
                
                worker._process_job(job_id)
            
            # Verify final status
            with real_get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                assert job.status == JobStatus.COMPLETED
                assert job.result is not None
                
                result = pickle.loads(job.result)
                assert result == "completed after 0.01"