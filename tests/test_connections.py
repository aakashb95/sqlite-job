import pickle
from unittest.mock import patch, MagicMock

import pytest

from sqlite_job.connections import SQLiteJob
from sqlite_job.models import Job, JobStatus, Queue


class TestSQLiteJob:
    """Test SQLiteJob class."""
    
    @pytest.fixture
    def sqlite_job(self):
        """Create SQLiteJob instance for testing."""
        return SQLiteJob("test_queue")
    
    def test_init(self, sqlite_job):
        """Test SQLiteJob initialization."""
        assert sqlite_job.default_queue_name == "test_queue"
    
    def test_enqueue_creates_queue_if_not_exists(self, test_db, sqlite_job):
        """Test that enqueue creates a queue if it doesn't exist."""
        with patch('sqlite_job.connections.get_session') as mock_get_session:
            # Mock session context manager
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock query to return None (queue doesn't exist)
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            # Mock job creation
            mock_job = MagicMock()
            mock_job.id = "test-job-id"
            mock_session.add.return_value = None
            mock_session.flush.return_value = None
            
            # Create a side effect for session.add that sets up the job
            def add_side_effect(obj):
                if isinstance(obj, Job):
                    obj.id = "test-job-id"
            
            mock_session.add.side_effect = add_side_effect
            
            result = sqlite_job.enqueue("test.function", 1, 2, keyword="value")
            
            # Verify queue was created
            queue_calls = [call for call in mock_session.add.call_args_list 
                          if call[0] and isinstance(call[0][0], Queue)]
            assert len(queue_calls) == 1
            assert queue_calls[0][0][0].name == "test_queue"
            
            # Verify job was created
            job_calls = [call for call in mock_session.add.call_args_list 
                        if call[0] and isinstance(call[0][0], Job)]
            assert len(job_calls) == 1
            
            assert result == "test-job-id"
    
    def test_enqueue_uses_existing_queue(self, test_db, sqlite_job):
        """Test that enqueue uses existing queue if it exists."""
        with patch('sqlite_job.connections.get_session') as mock_get_session:
            # Mock session context manager
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock existing queue
            existing_queue = Queue(name="test_queue")
            mock_session.query.return_value.filter.return_value.first.return_value = existing_queue
            
            # Mock job creation
            def add_side_effect(obj):
                if isinstance(obj, Job):
                    obj.id = "test-job-id"
            
            mock_session.add.side_effect = add_side_effect
            
            result = sqlite_job.enqueue("test.function", 1, 2)
            
            # Verify no new queue was created (only job was added)
            job_calls = [call for call in mock_session.add.call_args_list 
                        if call[0] and isinstance(call[0][0], Job)]
            queue_calls = [call for call in mock_session.add.call_args_list 
                          if call[0] and isinstance(call[0][0], Queue)]
            
            assert len(job_calls) == 1
            assert len(queue_calls) == 0  # No new queue created
            
            assert result == "test-job-id"
    
    def test_enqueue_serializes_function_data(self, test_db, sqlite_job):
        """Test that enqueue properly serializes function data."""
        with patch('sqlite_job.connections.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock existing queue
            existing_queue = Queue(name="test_queue")
            mock_session.query.return_value.filter.return_value.first.return_value = existing_queue
            
            # Capture the job that gets added
            added_jobs = []
            def add_side_effect(obj):
                if isinstance(obj, Job):
                    obj.id = "test-job-id"
                    added_jobs.append(obj)
            
            mock_session.add.side_effect = add_side_effect
            
            sqlite_job.enqueue("test.function", 1, 2, keyword="value")
            
            # Verify job data was serialized correctly
            assert len(added_jobs) == 1
            job = added_jobs[0]
            
            # Deserialize and check the function data
            unpickled_data = pickle.loads(job.function)
            assert unpickled_data["f"] == "test.function"
            assert unpickled_data["args"] == (1, 2)
            assert unpickled_data["kwargs"] == {"keyword": "value"}
            assert job.status == JobStatus.PENDING
            assert job.queue_name == "test_queue"
    
    def test_deserialize_job_valid_function(self, sqlite_job, mock_test_functions):
        """Test deserializing a valid job function."""
        # Serialize test data
        data = {"f": "tests.conftest.simple_add", "args": (5, 3), "kwargs": {}}
        pickled_data = pickle.dumps(data)
        
        # Mock the import to return our test function
        with patch('sqlite_job.connections.importlib.import_module') as mock_import:
            mock_module = MagicMock()
            mock_module.simple_add = mock_test_functions["simple_add"]
            mock_import.return_value = mock_module
            
            function, args, kwargs = sqlite_job.deserialize_job(pickled_data)
            
            assert function == mock_test_functions["simple_add"]
            assert args == (5, 3)
            assert kwargs == {}
            
            # Verify we can call the function
            result = function(*args, **kwargs)
            assert result == 8
    
    def test_deserialize_job_invalid_function_path(self, sqlite_job):
        """Test deserializing job with invalid function path format."""
        # Missing dot in function path
        data = {"f": "invalid_function_path", "args": (), "kwargs": {}}
        pickled_data = pickle.dumps(data)
        
        with pytest.raises(ValueError, match="Function path must be in 'module.function' format"):
            sqlite_job.deserialize_job(pickled_data)
    
    def test_deserialize_job_import_error(self, sqlite_job):
        """Test deserializing job with import error."""
        data = {"f": "nonexistent.module.function", "args": (), "kwargs": {}}
        pickled_data = pickle.dumps(data)
        
        with pytest.raises(ValueError, match="Cannot import function"):
            sqlite_job.deserialize_job(pickled_data)
    
    def test_deserialize_job_attribute_error(self, sqlite_job):
        """Test deserializing job with missing function attribute."""
        data = {"f": "sqlite_job.models.nonexistent_function", "args": (), "kwargs": {}}
        pickled_data = pickle.dumps(data)
        
        with pytest.raises(ValueError, match="Cannot import function"):
            sqlite_job.deserialize_job(pickled_data)
    
    def test_get_job_result_existing_job(self, sqlite_job):
        """Test getting result for existing job."""
        test_result = "test result"
        
        with patch('sqlite_job.connections.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock existing job
            mock_job = MagicMock()
            mock_job.result = test_result
            mock_session.query.return_value.filter.return_value.first.return_value = mock_job
            
            result = sqlite_job.get_job_result("test-job-id")
            
            assert result == test_result
            mock_session.query.assert_called_once_with(Job)
    
    def test_get_job_result_nonexistent_job(self, sqlite_job):
        """Test getting result for nonexistent job."""
        with patch('sqlite_job.connections.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # Mock no job found
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(ValueError, match="Job with id nonexistent-id not found"):
                sqlite_job.get_job_result("nonexistent-id")
    
    def test_enqueue_with_args_and_kwargs(self, test_db, sqlite_job):
        """Test enqueue with both positional and keyword arguments."""
        with patch('sqlite_job.connections.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            existing_queue = Queue(name="test_queue")
            mock_session.query.return_value.filter.return_value.first.return_value = existing_queue
            
            added_jobs = []
            def add_side_effect(obj):
                if isinstance(obj, Job):
                    obj.id = "test-job-id"
                    added_jobs.append(obj)
            
            mock_session.add.side_effect = add_side_effect
            
            sqlite_job.enqueue("test.complex_function", 1, 2, 3, key1="value1", key2="value2")
            
            # Verify serialized data
            job = added_jobs[0]
            unpickled_data = pickle.loads(job.function)
            
            assert unpickled_data["f"] == "test.complex_function"
            assert unpickled_data["args"] == (1, 2, 3)
            assert unpickled_data["kwargs"] == {"key1": "value1", "key2": "value2"}
    
    def test_enqueue_no_args(self, test_db, sqlite_job):
        """Test enqueue with no arguments."""
        with patch('sqlite_job.connections.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            existing_queue = Queue(name="test_queue")
            mock_session.query.return_value.filter.return_value.first.return_value = existing_queue
            
            added_jobs = []
            def add_side_effect(obj):
                if isinstance(obj, Job):
                    obj.id = "test-job-id"
                    added_jobs.append(obj)
            
            mock_session.add.side_effect = add_side_effect
            
            sqlite_job.enqueue("test.no_args_function")
            
            # Verify serialized data
            job = added_jobs[0]
            unpickled_data = pickle.loads(job.function)
            
            assert unpickled_data["f"] == "test.no_args_function"
            assert unpickled_data["args"] == ()
            assert unpickled_data["kwargs"] == {}