import time

from sqlite_job.connections import SQLiteJob


def add(a, b):
    return a + b


def delayed_add(a, b, delay=1):
    time.sleep(delay)
    return a + b


job_connection = SQLiteJob("default")
job_id = job_connection.enqueue("example.add", 1, 2)
print(job_id)

job_id2 = job_connection.enqueue("example.delayed_add", 3, 4, delay=2)
print(job_id2)
