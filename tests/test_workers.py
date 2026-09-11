from workers.base import JobInfo, JobState
from workers.cancellation import CancellationToken
from workers.queue import JobQueue


def test_job_states_match_persistent_contract():
    assert [state.value for state in JobState] == [
        "QUEUED", "PREPARING", "RUNNING", "PAUSED", "COMPLETED", "FAILED", "CANCELLED"
    ]


def test_queue_and_cancellation():
    queue = JobQueue()
    job = JobInfo(name="demo")
    queue.push(job)
    assert len(queue) == 1
    assert queue.pop() is job
    token = CancellationToken()
    token.cancel()
    assert token.is_cancelled
