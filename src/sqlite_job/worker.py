import pickle
import time

from sqlite_job.connections import SQLiteJob
from sqlite_job.db import get_session
from sqlite_job.models import Job, JobStatus


class Worker:
    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.job_connection = SQLiteJob(queue_name)

    def run(self):
        while True:
            job_id = self._get_job_id()
            if not job_id:
                print("No job found, sleeping for 1 second")
                time.sleep(1)
                continue
            self._process_job(job_id)

    def _get_job_id(self):
        with get_session() as session:
            print(f"Getting job from queue {self.queue_name}")
            job = (
                session.query(Job)
                .filter(
                    Job.status == JobStatus.PENDING,
                    Job.queue_name == self.queue_name,
                )
                .first()
            )
            print(f"Job: {job}")
            if not job:
                print("No job found")
                return None
            return job.id

    def _process_job(self, job_id: str):
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            job.status = JobStatus.RUNNING
            session.flush()
            
            function, args, kwargs = self.job_connection.deserialize_job(job)

        # Execute the job function
        result = function(*args, **kwargs)

        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            job.status = JobStatus.COMPLETED
            job.result = pickle.dumps(result)
            session.flush()
