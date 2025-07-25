import importlib
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

    def deserialize_job(self, job_or_data):
        unpickled_data = pickle.loads(job_or_data)

        function_path = unpickled_data["f"]
        args = unpickled_data["args"]
        kwargs = unpickled_data["kwargs"]

        # Parse module.function_name format
        if "." not in function_path:
            raise ValueError(
                f"Function path must be in 'module.function' format, got '{function_path}'"
            )

        module_name, function_name = function_path.rsplit(".", 1)

        # Dynamically import the module and get the function
        try:
            module = importlib.import_module(module_name)
            function = getattr(module, function_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Cannot import function '{function_path}': {e}")

        return function, args, kwargs

    def get_job_result(self, job_id: str):
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job with id {job_id} not found")
            return job.result
