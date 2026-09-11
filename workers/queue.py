from collections import deque
from workers.base import JobInfo


class JobQueue:
    def __init__(self) -> None:
        self._items: deque[JobInfo] = deque()

    def push(self, job: JobInfo) -> None:
        self._items.append(job)

    def pop(self) -> JobInfo:
        return self._items.popleft()

    def __len__(self) -> int:
        return len(self._items)
