import pickle
import time
from unittest.mock import patch, MagicMock, call

import pytest

from sqlite_job.models import Job, JobStatus, Queue
from sqlite_job.worker import Worker


class TestWorker:
    """Test Worker class."""
    
    @pytest.fixture
    def worker(self):
        """Create Worker instance for testing."""
        return Worker("test_queue")
    
    def test_init(self, worker):
        """Test Worker initialization."""
        assert worker.queue_name == "test_queue"
        assert worker.job_connection is not None
        assert worker.job_connection.default_queue_name == "test_queue"
    
    def test_get_job_id_with_pending_job(self, worker):
        """Test _get_job_id returns job ID when pending job exists."""
        with patch('sqlite_job.worker.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock a pending job
            mock_job = MagicMock()
            mock_job.id = "test-job-id"
            mock_session.query.return_value.filter.return_value.first.return_value = mock_job
            
            job_id = worker._get_job_id()
            
            assert job_id == "test-job-id"
            
            # Verify the query was constructed correctly
            mock_session.query.assert_called_once_with(Job)
            filter_call = mock_session.query.return_value.filter.call_args[0]
            # The filter should check for PENDING status and correct queue name
            assert len(filter_call) == 2  # Two filter conditions
    
    def test_get_job_id_no_pending_jobs(self, worker):
        """Test _get_job_id returns None when no pending jobs exist."""
        with patch('sqlite_job.worker.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock no pending jobs
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            job_id = worker._get_job_id()
            
            assert job_id is None
    
    def test_process_job_successful_execution(self, worker, mock_test_functions):
        """Test _process_job successfully executes a job."""
        job_id = "test-job-id"
        test_function_data = {"f": "test.simple_add", "args": (5, 3), "kwargs": {}}
        pickled_function_data = pickle.dumps(test_function_data)
        
        with patch('sqlite_job.worker.get_session') as mock_get_session:
            # Mock sessions for getting job data and updating status
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock job for initial status update and function data retrieval
            mock_job_initial = MagicMock()
            mock_job_initial.function = pickled_function_data
            mock_job_initial.status = JobStatus.PENDING
            
            # Mock job for final status update
            mock_job_final = MagicMock()
            mock_job_final.status = JobStatus.RUNNING
            
            # Mock query to return different job instances for different calls
            def query_side_effect(*args):
                mock_query = MagicMock()
                mock_filter = MagicMock()
                mock_query.filter.return_value = mock_filter
                
                # First call (get function data), second call (update result)
                call_count = getattr(query_side_effect, 'call_count', 0)
                query_side_effect.call_count = call_count + 1
                
                if call_count == 0:
                    mock_filter.first.return_value = mock_job_initial
                else:
                    mock_filter.first.return_value = mock_job_final
                
                return mock_query
            
            mock_session.query.side_effect = query_side_effect
            
            # Mock the job_connection.deserialize_job method
            with patch.object(worker.job_connection, 'deserialize_job') as mock_deserialize:
                mock_deserialize.return_value = (
                    mock_test_functions["simple_add"], 
                    (5, 3), 
                    {}
                )
                
                worker._process_job(job_id)
                
                # Verify deserialize was called with correct data
                mock_deserialize.assert_called_once_with(pickled_function_data)
                
                # Verify job status was updated to RUNNING initially
                assert mock_job_initial.status == JobStatus.RUNNING
                
                # Verify job status was updated to COMPLETED finally
                assert mock_job_final.status == JobStatus.COMPLETED
                
                # Verify result was pickled and stored
                expected_result = pickle.dumps(8)  # 5 + 3 = 8
                assert mock_job_final.result == expected_result
                
                # Verify flush was called to commit changes
                assert mock_session.flush.call_count >= 2
    
    def test_process_job_with_kwargs(self, worker, mock_test_functions):
        """Test _process_job with function that uses kwargs."""
        job_id = "test-job-id"
        test_function_data = {"f": "test.function_with_kwargs", "args": (5,), "kwargs": {"b": 15, "c": 25}}
        pickled_function_data = pickle.dumps(test_function_data)
        
        with patch('sqlite_job.worker.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            mock_job_initial = MagicMock()
            mock_job_initial.function = pickled_function_data
            
            mock_job_final = MagicMock()
            
            def query_side_effect(*args):
                mock_query = MagicMock()
                mock_filter = MagicMock()
                mock_query.filter.return_value = mock_filter
                
                call_count = getattr(query_side_effect, 'call_count', 0)
                query_side_effect.call_count = call_count + 1
                
                if call_count == 0:
                    mock_filter.first.return_value = mock_job_initial
                else:
                    mock_filter.first.return_value = mock_job_final
                
                return mock_query
            
            mock_session.query.side_effect = query_side_effect
            
            with patch.object(worker.job_connection, 'deserialize_job') as mock_deserialize:
                mock_deserialize.return_value = (
                    mock_test_functions["function_with_kwargs"], 
                    (5,), 
                    {"b": 15, "c": 25}
                )
                
                worker._process_job(job_id)
                
                # Verify result is correct: 5 + 15 + 25 = 45
                expected_result = pickle.dumps(45)
                assert mock_job_final.result == expected_result
                assert mock_job_final.status == JobStatus.COMPLETED
    
    @patch('sqlite_job.worker.time.sleep')
    def test_run_processes_jobs_continuously(self, mock_sleep, worker):
        """Test that run method continuously processes jobs."""
        # Mock _get_job_id to return job IDs then None to break the loop
        job_ids = ["job-1", "job-2", None]  # None will break the loop after 2 jobs
        
        with patch.object(worker, '_get_job_id', side_effect=job_ids):
            with patch.object(worker, '_process_job') as mock_process_job:
                # Add a side effect to break the loop after processing 2 jobs
                def process_job_side_effect(job_id):
                    if job_id == "job-2":
                        # Raise an exception to break the infinite loop for testing
                        raise KeyboardInterrupt()
                
                mock_process_job.side_effect = process_job_side_effect
                
                with pytest.raises(KeyboardInterrupt):
                    worker.run()
                
                # Verify jobs were processed
                expected_calls = [call("job-1"), call("job-2")]
                mock_process_job.assert_has_calls(expected_calls)
                
                # Verify sleep was called when no job was available
                # (This happens after job-2 when _get_job_id returns None)
                mock_sleep.assert_called_with(1)
    
    @patch('sqlite_job.worker.time.sleep')
    def test_run_sleeps_when_no_jobs(self, mock_sleep, worker):
        """Test that run method sleeps when no jobs are available."""
        # Mock _get_job_id to always return None
        with patch.object(worker, '_get_job_id', return_value=None):
            with patch.object(worker, '_process_job') as mock_process_job:
                # Use a counter to break the loop after a few iterations
                sleep_counter = [0]
                def sleep_side_effect(duration):
                    sleep_counter[0] += 1
                    if sleep_counter[0] >= 3:  # Break after 3 sleep calls
                        raise KeyboardInterrupt()
                
                mock_sleep.side_effect = sleep_side_effect
                
                with pytest.raises(KeyboardInterrupt):
                    worker.run()
                
                # Verify no jobs were processed
                mock_process_job.assert_not_called()
                
                # Verify sleep was called multiple times
                assert mock_sleep.call_count == 3
                mock_sleep.assert_called_with(1)
    
    def test_process_job_handles_session_separately(self, worker, mock_test_functions):
        """Test that _process_job properly handles sessions to avoid locks during imports."""
        job_id = "test-job-id"
        test_function_data = {"f": "test.simple_add", "args": (1, 2), "kwargs": {}}
        pickled_function_data = pickle.dumps(test_function_data)
        
        with patch('sqlite_job.worker.get_session') as mock_get_session:
            # Track the number of session context manager entries
            session_entries = []
            
            def session_context_manager():
                mock_session = MagicMock()
                session_entries.append(mock_session)
                
                # Mock the context manager
                context_manager = MagicMock()
                context_manager.__enter__.return_value = mock_session
                context_manager.__exit__.return_value = None
                return context_manager
            
            mock_get_session.side_effect = session_context_manager
            
            # Setup mock jobs for each session
            mock_job_1 = MagicMock()
            mock_job_1.function = pickled_function_data
            
            mock_job_2 = MagicMock()
            
            session_entries[0].query.return_value.filter.return_value.first.return_value = mock_job_1
            
            # Mock the deserialize method
            with patch.object(worker.job_connection, 'deserialize_job') as mock_deserialize:
                mock_deserialize.return_value = (
                    mock_test_functions["simple_add"], 
                    (1, 2), 
                    {}
                )
                
                # Mock second session for final update
                def get_session_side_effect():
                    if len(session_entries) == 1:
                        # First session already created above
                        return session_entries[0]
                    else:
                        # Create second session for final update
                        mock_session_2 = MagicMock()
                        mock_session_2.query.return_value.filter.return_value.first.return_value = mock_job_2
                        session_entries.append(mock_session_2)
                        
                        context_manager = MagicMock()
                        context_manager.__enter__.return_value = mock_session_2
                        context_manager.__exit__.return_value = None
                        return context_manager
                
                # Reset and setup the side effect properly
                session_entries.clear()
                mock_get_session.side_effect = None
                mock_get_session.return_value = session_context_manager()
                
                worker._process_job(job_id)
                
                # Verify that get_session was called multiple times (separate sessions)
                assert mock_get_session.call_count >= 2
                
                # Verify deserialize was called with the function data
                mock_deserialize.assert_called_once_with(pickled_function_data)