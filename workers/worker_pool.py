from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable


class WorkerPool:
    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="spvs")

    def submit(self, fn: Callable[..., object], *args: object, **kwargs: object) -> Future[object]:
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
