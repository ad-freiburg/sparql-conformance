"""Tests for the raw HTTP protocol transport."""

from sparql_conformance.protocol_tools import (
    _ensure_connection_close,
    _set_content_length,
    send_raw_http,
)


def test_connection_close_is_added_when_missing():
    request_head = (
        "GET /sparql HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "\r\n"
    )

    result = _ensure_connection_close(request_head)

    assert result.endswith("\r\n\r\n")
    assert result.count("Connection: close") == 1


def test_existing_connection_header_is_preserved():
    request_head = (
        "GET /sparql HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Connection: keep-alive\r\n"
        "\r\n"
    )

    result = _ensure_connection_close(request_head)

    assert "Connection: keep-alive" in result
    assert "Connection: close" not in result


def test_connection_header_detection_is_case_insensitive():
    request_head = (
        "GET /sparql HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "cOnNeCtIoN: close\r\n"
        "\r\n"
    )

    result = _ensure_connection_close(request_head)

    assert result.count("cOnNeCtIoN: close") == 1
    assert "Connection: close" not in result


def test_connection_close_keeps_updated_content_length():
    request_head = (
        "POST /sparql HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Content-Length: 99\r\n"
        "\r\n"
    )

    result = _ensure_connection_close(
        _set_content_length(request_head, 4)
    )

    assert result.count("Content-Length:") == 1
    assert "Content-Length: 4" in result
    assert "Connection: close" in result


def test_raw_http_transport_sends_connection_close(monkeypatch):
    class FakeSocket:
        def __init__(self):
            self.sent = b""
            self.responses = [
                b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n",
                b"",
            ]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def settimeout(self, timeout):
            pass

        def sendall(self, data):
            self.sent = data

        def recv(self, size):
            return self.responses.pop(0)

    sock = FakeSocket()
    monkeypatch.setattr(
        "sparql_conformance.protocol_tools.socket.create_connection",
        lambda *args, **kwargs: sock,
    )

    response = send_raw_http(
        "localhost",
        7001,
        "GET /sparql HTTP/1.1\r\nHost: localhost\r\n\r\n",
        "",
        "utf-8",
    )

    assert b"Connection: close\r\n" in sock.sent
    assert response.startswith("HTTP/1.1 200 OK")
