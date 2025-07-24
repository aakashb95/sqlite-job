import pickle

from sqlite_job.db import get_session
from sqlite_job.models import Job, JobStatus, Queue


class SQLiteJob:
    def __init__(self, default_queue_name: str):
        self.default_queue_name = default_queue_name

    def enqueue(self, function: str, *args, **kwargs):
        data = {"f": function, "args": args, "kwargs": kwargs}
        pickled_data = pickle.dumps(data)

        with get_session() as session:
            queue = (
                session.query(Queue)
                .filter(Queue.name == self.default_queue_name)
                .first()
            )
            if not queue:
                queue = Queue(name=self.default_queue_name)
                session.add(queue)
        job_id = None
        with get_session() as session:
            job = Job(
                function=pickled_data,
                queue_name=self.default_queue_name,
                status=JobStatus.PENDING,
            )
            session.add(job)
            session.flush()
            job_id = job.id

        return job_id

    def deserialize_job(self, job: Job):
        unpickled_data = pickle.loads(job.function)
        function = unpickled_data["f"]
        args = unpickled_data["args"]
        kwargs = unpickled_data["kwargs"]
        return function, args, kwargs
