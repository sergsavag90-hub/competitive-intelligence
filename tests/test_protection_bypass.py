import pytest

from src.utils.protection.proxy_manager import ProxyManager
from src.utils.protection.captcha_solver import CaptchaSolver
from src.utils.protection.circuit_breaker import SeleniumCircuitBreaker


def test_proxy_rotation_empty_pool():
    mgr = ProxyManager()
    assert mgr.get_residential_proxy() is None


def test_circuit_breaker_opens():
    cb = SeleniumCircuitBreaker(threshold=2, reset_timeout=1)
    assert cb.can_execute()
    cb.record_failure()
    assert cb.can_execute()
    cb.record_failure()
    assert cb.state == "OPEN"
    assert not cb.can_execute()


def test_captcha_solver_no_key():
    solver = CaptchaSolver(api_key=None)
    assert solver.solve("dummy", "https://example.com") is None
