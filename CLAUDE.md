# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `sqlite-job`, a Python job queue system that uses SQLite as the backing store. The system allows enqueueing Python functions to be executed asynchronously by worker processes.

## Architecture

The codebase follows a simple layered architecture:

- **Models Layer** (`models.py`): SQLAlchemy models for `Job` and `Queue` tables with job status tracking (PENDING, RUNNING, COMPLETED, FAILED)
- **Database Layer** (`db.py`): SQLite engine configuration and session management with context managers
- **Connection Layer** (`connections.py`): `SQLiteJob` class that handles job enqueueing, serialization (pickle), and result retrieval
- **Worker Layer** (`worker.py`): `Worker` class that polls for pending jobs and executes them by dynamically importing functions
- **Settings Layer** (`settings.py`): Configuration for worker function registration (currently minimal)

## Key Components

### Job Processing Flow
1. Functions are enqueued via `SQLiteJob.enqueue()` with module.function_name format
2. Jobs are serialized using pickle and stored in SQLite
3. Workers poll for PENDING jobs in their assigned queue
4. Functions are dynamically imported and executed
5. Results are pickled and stored back in the database

### Database Schema
- **jobs table**: id, function (pickled), result (pickled), status, queue_name, timestamps
- **queues table**: name, timestamps
- Uses UUID primary keys for jobs

## Development Commands

This project uses `uv` as the package manager:

```bash
# Install dependencies and sync environment
uv sync

# Run the main CLI entry point
uv run sqlite-job

# Run the worker process
uv run python src/sqlite_job/main.py

# Run example jobs
uv run python src/example.py

# Build the package
uv build

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=sqlite_job --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_models.py

# Run tests with verbose output
uv run pytest -v
```

## Database

The SQLite database file is created at `src/sqlite_job.db` and tables are auto-created on import of `models.py`. No migrations are currently implemented.