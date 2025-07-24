from sqlite_job.worker import Worker

if __name__ == "__main__":
    worker = Worker("default")
    worker.run()
