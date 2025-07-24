from sqlite_job.connections import SQLiteJob


def add(a, b):
    return a + b


job_connection = SQLiteJob("default")
job_id = job_connection.enqueue("add", 1, 2)
print(job_id)
