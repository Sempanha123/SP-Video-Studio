from workers.base import JobInfo


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobInfo] = {}

    def register(self, job: JobInfo) -> None:
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> JobInfo | None:
        return self._jobs.get(job_id)

    def all(self) -> tuple[JobInfo, ...]:
        return tuple(self._jobs.values())
