import pickle

from sqlite_job.db import get_session
from sqlite_job.models import Job, JobStatus, Queue
from sqlite_job.settings import WorkerSettings


class SQLiteJob:
    def __init__(self, default_queue_name: str, settings: WorkerSettings):
        self.default_queue_name = default_queue_name
        self.settings = settings

    def enqueue(self, function: str, *args, **kwargs):
        data = {"f": function, "args": args, "kwargs": kwargs}
        pickled_data = pickle.dumps(data)

        with get_session(self.settings.database_path) as session:
            queue = (
                session.query(Queue)
                .filter(Queue.name == self.default_queue_name)
                .first()
            )
            if not queue:
                queue = Queue(name=self.default_queue_name)
                session.add(queue)
        job_id = None
        with get_session(self.settings.database_path) as session:
            job = Job(
                function=pickled_data,
                queue_name=self.default_queue_name,
                status=JobStatus.PENDING,
            )
            session.add(job)
            session.flush()
            job_id = job.id

        return job_id

    def deserialize_job(self, job_or_data, settings):
        unpickled_data = pickle.loads(job_or_data)

        function_name = unpickled_data["f"]
        args = unpickled_data["args"]
        kwargs = unpickled_data["kwargs"]

        # Use WorkerSettings to get function - this is the only way
        function = settings.get_function(function_name)
        return function, args, kwargs

    def get_job_result(self, job_id: str):
        with get_session(self.settings.database_path) as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job with id {job_id} not found")
            if job.result is None:
                return None
            return pickle.loads(job.result)
