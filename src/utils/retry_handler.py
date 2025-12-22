from tenacity import Retrying, stop_after_attempt, wait_exponential


def build_retrying(max_attempts: int = 3):
    return Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
