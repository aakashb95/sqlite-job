import time

from sqlite_job.connections import SQLiteJob
from sqlite_job.settings import WorkerSettings
from sqlite_job.worker import Worker


def add(a, b):
    return a + b


def delayed_add(a, b, delay=1):
    time.sleep(delay)
    return a + b


# WorkerSettings with registered functions - THIS IS MANDATORY
class MyWorkerSettings(WorkerSettings):
    functions = [add, delayed_add]


if __name__ == "__main__":
    # Enqueue jobs using simple function names
    job_connection = SQLiteJob("default")
    job_id = job_connection.enqueue("add", 12, 22)
    job_id2 = job_connection.enqueue("delayed_add", 123, 456, delay=2)

    print(f"Enqueued jobs: {job_id}, {job_id2}")

    # Workers MUST be created with WorkerSettings
    print("Starting worker...")
    worker = Worker("default", MyWorkerSettings())
    
    # Process a few jobs then exit for demo
    for _ in range(3):
        next_job_id = worker._get_job_id()
        if next_job_id:
            print(f"Processing job: {next_job_id}")
            worker._process_job(next_job_id)
        else:
            print("No more jobs to process")
            break

    # Check results
    result1 = job_connection.get_job_result(job_id)
    result2 = job_connection.get_job_result(job_id2)
    print(f"Results: {result1}, {result2}")
