import pytest
from fastapi.testclient import TestClient

from backend.fastapi_app import app


@pytest.mark.skip(reason="WS integration placeholder")
def test_ws_connects():
    client = TestClient(app)
    with client.websocket_connect("/ws/scan/testjob") as ws:
        ws.send_text("ping")
        assert ws.receive_text() is not None
