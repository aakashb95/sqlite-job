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

```python
import time
from sqlite_job.settings import WorkerSettings
from sqlite_job.connections import SQLiteJob
from sqlite_job.worker import Worker

# Define whatever functions you want to run as background jobs
def add_numbers(a, b):
    return a + b

def process_data(items, multiplier=2):
    time.sleep(1)  # pretend this takes time
    return [x * multiplier for x in items]

# Register your functions and specify database location
class MyWorkerSettings(WorkerSettings):
    functions = [add_numbers, process_data]

# Create settings with database path
settings = MyWorkerSettings("my_jobs.db")

# Now you can queue up jobs using simple function names
job_conn = SQLiteJob("default", settings)
job1 = job_conn.enqueue("add_numbers", 10, 20)
job2 = job_conn.enqueue("process_data", [1, 2, 3, 4], multiplier=3)

print(f"Enqueued jobs: {job1}, {job2}")

# In real life, you'd run this worker in a separate process
# but for this example we'll just process the jobs right here
worker = Worker("default", settings)

# grab and process our jobs
for _ in range(2):  # we know we have 2 jobs
    job_id = worker._get_job_id()
    if job_id:
        worker._process_job(job_id)

# check what happened
result1 = job_conn.get_job_result(job1)
result2 = job_conn.get_job_result(job2)

print(f"Results: {result1}, {result2}")  # should be 30, [3, 6, 9, 12]
```

## Production Setup

In production, you'll typically have two separate files:

### 1. Job Enqueueing (`enqueue_jobs.py`)

```python
from sqlite_job.connections import SQLiteJob
from sqlite_job.settings import WorkerSettings
import time

# Define your functions
def send_email(to, subject, body):
    # your email sending logic
    return f"Sent email to {to}"

def process_payment(user_id, amount):
    time.sleep(3)
    # your payment processing logic
    return f"Processed ${amount} for user {user_id}"

# Register functions and specify database location
class AppWorkerSettings(WorkerSettings):
    functions = [send_email, process_payment]

# Create settings instance with database path
settings = AppWorkerSettings("production_jobs.db")

# Enqueue jobs from your application
def enqueue_email_job():
    job_conn = SQLiteJob("default", settings)
    job_id = job_conn.enqueue("send_email", "user@example.com", "Welcome", "Thanks for signing up!")
    return job_id

def enqueue_payment_job():
    job_conn = SQLiteJob("default", settings) 
    job_id = job_conn.enqueue("process_payment", 123, 99.99)
    return job_id
```

### 2. Worker Process (`worker.py`)

```python
from sqlite_job.worker import Worker
from enqueue_jobs import settings  # Import the same settings instance

# Create worker with the same settings (same database, same functions)
worker = Worker("default", settings)

# Run worker - this blocks and processes jobs forever
if __name__ == "__main__":
    print("Starting worker...")
    worker.run()  # Runs indefinitely, processing jobs as they arrive
```

Run the worker as a separate process: `python worker.py`

## How It Works

Functions are registered in a `WorkerSettings` class, then jobs are enqueued using simple function names rather than module paths. Workers poll for pending jobs and execute them using the registered function registry.

## Multiple Queues

Different queues allow you to segregate work types and run specialized workers:

```python
def send_email(email): return f"Email sent to {email}"
def analyze_data(dataset): return f"Analyzed {len(dataset)} items"

# Email queue worker settings
class EmailWorkerSettings(WorkerSettings):
    functions = [send_email]

# Data processing queue worker settings
class DataWorkerSettings(WorkerSettings):
    functions = [analyze_data]

# Create settings instances with database paths
email_settings = EmailWorkerSettings("email_jobs.db")
data_settings = DataWorkerSettings("data_jobs.db")

# Enqueue to specific queues with their respective settings
SQLiteJob("email", email_settings).enqueue("send_email", "user@example.com")
SQLiteJob("data_processing", data_settings).enqueue("analyze_data", [1, 2, 3])

# Run specialized workers with matching settings
email_worker = Worker("email", email_settings)
data_worker = Worker("data_processing", data_settings)
```

## Error Handling

Jobs that raise exceptions are marked as FAILED. The worker continues processing subsequent jobs.

```python
from sqlite_job.connections import SQLiteJob
from sqlite_job.settings import WorkerSettings

def risky_operation():
    raise ValueError("Something went wrong")

class MySettings(WorkerSettings):
    functions = [risky_operation]

# Create settings with database path
settings = MySettings("error_test.db")

# Job will fail gracefully without crashing the worker
job_conn = SQLiteJob("default", settings)
job_conn.enqueue("risky_operation")
```

## Database

The SQLite database file is created at the path you specify in `WorkerSettings(database_path)`. The database is created in your current working directory when you first enqueue a job. Database tables are created automatically - no setup required.

Both your job enqueueing code and worker processes must use the same `WorkerSettings` instance to ensure they access the same database.

## Requirements

- Python 3.11+
- SQLAlchemy
- No external message brokers or databases required

## License

MIT