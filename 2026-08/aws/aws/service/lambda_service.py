"""Lambda invocation over the Docker Engine API (Podman-compatible socket).

Invoking a function runs a container from the image registered under that
function name in ``FUNCTIONS`` (name -> container-create spec, at minimum an
``image``).  The event payload is passed to the container as the
``LAMBDA_EVENT`` environment variable (base64); the container's combined
stdout/stderr is returned as the Lambda response.  Only Invoke is implemented;
other Lambda APIs come later.
"""

from __future__ import annotations

import base64
import json
import socket
from http.client import HTTPConnection

# Function name -> container-create spec (e.g. {"image": "alpine", "Cmd": [...]}).
# Every request reads/writes this dict; tests replace it (monkeypatch) to keep
# each run hermetic.
FUNCTIONS: dict[str, dict] = {}

# Docker-compatible engine socket (Podman machine).  Override in tests via
# monkeypatch if a non-default location is needed.
DOCKER_SOCKET = "/var/run/docker.sock"
API_VERSION = "v1.40"


class FunctionNotFound(Exception):
    """Raised when the requested function is not registered."""


class _UnixHTTPConnection(HTTPConnection):
    def __init__(self, path: str) -> None:
        super().__init__("localhost")
        self._path = path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self._path)


def docker_request(method: str, path: str, body: bytes | None = None,
                   headers: dict | None = None) -> tuple[int, bytes]:
    """Raw Docker Engine API call over the unix socket."""
    conn = _UnixHTTPConnection(DOCKER_SOCKET)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def invoke_function(name: str, payload: bytes) -> tuple[bytes, int]:
    """Run the function's container; return (output, exit_code)."""
    spec = FUNCTIONS.get(name)
    if spec is None:
        raise FunctionNotFound(name)

    create = dict(spec)
    create["Tty"] = True
    create["Env"] = [f"LAMBDA_EVENT={base64.b64encode(payload).decode()}"]

    status, data = docker_request(
        "POST", f"/{API_VERSION}/containers/create",
        json.dumps(create).encode(), {"Content-Type": "application/json"},
    )
    if status not in (200, 201):
        raise RuntimeError(f"docker create failed: {status} {data.decode()!r}")
    cid = json.loads(data)["Id"]

    try:
        docker_request("POST", f"/{API_VERSION}/containers/{cid}/start")
        _, wait = docker_request("POST", f"/{API_VERSION}/containers/{cid}/wait")
        exit_code = json.loads(wait).get("StatusCode", -1)
        _, output = docker_request(
            "GET", f"/{API_VERSION}/containers/{cid}/logs?stdout=1&stderr=1",
        )
    finally:
        docker_request("DELETE", f"/{API_VERSION}/containers/{cid}")

    return output.strip(), exit_code
