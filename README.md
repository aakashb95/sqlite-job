# sqlite-job

A simple Python job queue system using SQLite as the backing store.

## Overview

sqlite-job allows you to enqueue Python functions for asynchronous execution by worker processes. Jobs are stored in SQLite, making it easy to deploy without additional infrastructure.

## Key Features

- Simple function-based job enqueueing
- SQLite backend - no external dependencies
- Worker settings pattern for clean function registration  
- Pickle serialization for arguments and results
- Multiple queue support
- Job status tracking (PENDING, RUNNING, COMPLETED, FAILED)

## Installation

```bash
pip install git+https://github.com/aakashb95/sqlite-job.git
```

## Quick Start

### 1. Define your functions and worker settings

```python
# my_tasks.py
import time
from sqlite_job.settings import WorkerSettings

def add_numbers(a, b):
    return a + b

def process_data(items, multiplier=2):
    time.sleep(1)  # Simulate work
    return [x * multiplier for x in items]

class MyWorkerSettings(WorkerSettings):
    functions = [add_numbers, process_data]
```

### 2. Enqueue jobs

```python
# enqueue_jobs.py
from sqlite_job.connections import SQLiteJob

job_conn = SQLiteJob("default")

# Enqueue jobs using simple function names
job1 = job_conn.enqueue("add_numbers", 10, 20)
job2 = job_conn.enqueue("process_data", [1, 2, 3, 4], multiplier=3)

print(f"Enqueued jobs: {job1}, {job2}")
```

### 3. Run a worker

```python
# worker.py  
from sqlite_job.worker import Worker
from my_tasks import MyWorkerSettings

# Workers require WorkerSettings
worker = Worker("default", MyWorkerSettings())
worker.run()  # Runs forever, processing jobs
```

### 4. Get results

```python
from sqlite_job.connections import SQLiteJob

job_conn = SQLiteJob("default")
result = job_conn.get_job_result(job_id)
print(result)  # 30 for the add_numbers job
```

## How It Works

1. **Function Registration**: Functions are registered in a `WorkerSettings` class
2. **Job Enqueueing**: Jobs are enqueued using simple function names, not module paths
3. **Worker Processing**: Workers poll for pending jobs and execute registered functions
4. **Result Storage**: Results are pickled and stored back in SQLite

## WorkerSettings Pattern

sqlite-job uses a mandatory WorkerSettings pattern inspired by arq:

- All functions must be registered in `WorkerSettings.functions`
- Workers require a WorkerSettings instance (no defaults)
- Jobs are enqueued using simple names like `"add_numbers"`
- No import path concerns - functions resolved via registry

```python
class MyWorkerSettings(WorkerSettings):
    functions = [
        my_function,
        another_function,
        # Add all your job functions here
    ]

# This is mandatory - no Worker() without settings
worker = Worker("queue_name", MyWorkerSettings())
```

## Multiple Queues

```python
# Different queues for different types of work
email_job = SQLiteJob("email").enqueue("send_email", "user@example.com")
data_job = SQLiteJob("data_processing").enqueue("analyze_data", dataset)

# Run workers for specific queues
email_worker = Worker("email", EmailWorkerSettings())
data_worker = Worker("data_processing", DataWorkerSettings())
```

## Error Handling

Jobs that raise exceptions will be marked as FAILED. The worker continues processing other jobs.

```python
def might_fail():
    raise ValueError("Something went wrong")

class MySettings(WorkerSettings):
    functions = [might_fail]

# Job will be marked as FAILED, worker continues
job_conn.enqueue("might_fail")
```

##  Database Location

By default, the SQLite database is created at `sqlite_job.db` in your working directory. Tables are created automatically.

## Requirements

- Python 3.8+
- SQLAlchemy
- No external message brokers or databases required

## License

MIT