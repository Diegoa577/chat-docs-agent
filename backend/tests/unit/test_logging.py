import logging

import pytest

from app.core.logging import _NoisyEndpointFilter


def _record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )


@pytest.mark.parametrize("path", ["/health", "/ready", "/metrics"])
def test_filter_drops_noisy_endpoints(path: str) -> None:
    record = _record(f'172.21.0.1:55352 - "GET {path} HTTP/1.1" 200 OK')
    assert _NoisyEndpointFilter().filter(record) is False


@pytest.mark.parametrize("path", ["/chat/stream", "/documents", "/conversations"])
def test_filter_keeps_regular_endpoints(path: str) -> None:
    record = _record(f'172.21.0.1:55352 - "GET {path} HTTP/1.1" 200 OK')
    assert _NoisyEndpointFilter().filter(record) is True
