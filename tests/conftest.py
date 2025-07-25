import os
import tempfile
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sqlite_job.models import Base


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database for each test function."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    # Create test engine
    test_engine = create_engine(f"sqlite:///{test_db_path}")
    
    # Create all tables
    Base.metadata.create_all(test_engine)
    
    yield test_engine
    
    # Cleanup
    os.unlink(test_db_path)


@pytest.fixture
def test_session(test_db):
    """Create a test database session."""
    @contextmanager
    def _get_test_session():
        session = Session(test_db)
        try:
            yield session
        finally:
            session.commit()
            session.close()
    
    return _get_test_session


@pytest.fixture
def mock_test_functions():
    """Mock functions for testing job execution."""
    def simple_add(a, b):
        return a + b
    
    def simple_multiply(x, y):
        return x * y
    
    def function_with_kwargs(a, b=10, c=20):
        return a + b + c
    
    def function_that_raises():
        raise ValueError("Test error")
    
    return {
        "simple_add": simple_add,
        "simple_multiply": simple_multiply,
        "function_with_kwargs": function_with_kwargs,
        "function_that_raises": function_that_raises,
    }