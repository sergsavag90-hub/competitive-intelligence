import time
from typing import Optional


class SeleniumCircuitBreaker:
    """Simple circuit breaker to pause scraping after repeated failures."""

    def __init__(self, threshold: int = 5, reset_timeout: int = 60):
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.threshold:
            self.state = "OPEN"

    def record_success(self) -> None:
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "OPEN":
            if self.last_failure_time is None:
                return False
            if (time.time() - self.last_failure_time) > self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True
