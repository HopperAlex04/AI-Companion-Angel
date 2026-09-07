from datetime import datetime, timezone
import logging
import time
import uuid


class RequestLog:
    """Tracks request timing and emits structured start/complete/fail logs."""

    def __init__(self, endpoint: str, *, label: str = "Request"):
        self.request_id = str(uuid.uuid4())
        self.endpoint = endpoint
        self.label = label
        self.start_time_perf = time.perf_counter()
        self.start_time_log = datetime.now(timezone.utc)
        logging.info(
            f"{self.label} {self.request_id} started",
            extra={
                "request_id": self.request_id,
                "endpoint": self.endpoint,
                "start_time_log": self.start_time_log,
            },
        )

    def _duration(self) -> float:
        return round(time.perf_counter() - self.start_time_perf, 2)

    def complete(self, status: int) -> None:
        logging.info(
            f"{self.label} {self.request_id} completed",
            extra={
                "request_id": self.request_id,
                "endpoint": self.endpoint,
                "end_time_log": datetime.now(timezone.utc),
                "duration": self._duration(),
                "status": status,
            },
        )

    def fail(self, error: BaseException, status: int = 500) -> None:
        logging.error(
            f"{self.label} {self.request_id} failed",
            extra={
                "request_id": self.request_id,
                "endpoint": self.endpoint,
                "end_time_log": datetime.now(timezone.utc),
                "duration": self._duration(),
                "status": status,
                "error": str(error),
            },
        )
