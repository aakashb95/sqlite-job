import pickle
import time

from sqlite_job.connections import SQLiteJob
from sqlite_job.db import get_session
from sqlite_job.models import Job, JobStatus
from sqlite_job.settings import WorkerSettings


class Worker:
    def __init__(self, queue_name: str, settings: WorkerSettings):
        self.queue_name = queue_name
        self.settings = settings
        self.job_connection = SQLiteJob(queue_name, settings)

    def run(self):
        while True:
            job_id = self._get_job_id()
            if not job_id:
                time.sleep(1)
                continue
            self._process_job(job_id)

    def _get_job_id(self):
        with get_session(self.settings.database_path) as session:
            job = (
                session.query(Job)
                .filter(
                    Job.status == JobStatus.PENDING,
                    Job.queue_name == self.queue_name,
                )
                .first()
            )
            if not job:
                return None
            return job.id

    def _process_job(self, job_id: str):
        # Get job data and deserialize outside of session context
        with get_session(self.settings.database_path) as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            job.status = JobStatus.RUNNING
            session.flush()
            # Access job.function while still in session to avoid detached instance
            job_function_data = job.function

        # Deserialize job outside of session to avoid locks during imports
        function, args, kwargs = self.job_connection.deserialize_job(job_function_data, self.settings)

        # Execute the job function
        result = function(*args, **kwargs)

        with get_session(self.settings.database_path) as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            job.status = JobStatus.COMPLETED
            job.result = pickle.dumps(result)
            print(f"Job {job_id} completed with result {result}")
            session.flush()
