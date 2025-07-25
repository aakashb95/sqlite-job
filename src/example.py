import time

from sqlite_job.connections import SQLiteJob


def add(a, b):
    return a + b


def delayed_add(a, b, delay=1):
    time.sleep(delay)
    return a + b


job_connection = SQLiteJob("default")
job_id = job_connection.enqueue("example.add", 12, 22)

job_id2 = job_connection.enqueue("example.delayed_add", 123, 456, delay=2)


# get job_result
job_result = job_connection.get_job_result(job_id)
print(job_result)

job_result2 = job_connection.get_job_result(job_id2)
print(job_result2)
