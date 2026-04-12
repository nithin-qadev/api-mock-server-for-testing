# API Mock Server

A lightweight, configurable mock API server built with Python and Flask.
Designed for use in test automation frameworks — define mocks via YAML or at runtime through a REST admin API.

---

## Quick Start

### Run locally

```bash
pip install -r requirements.txt
python server.py
```

### Run with Docker

```bash
docker compose up
```

Server starts on **http://localhost:8000**

---

## Defining Mocks

### Option 1 — YAML file (loaded on startup)

Edit `mocks/example.yaml` (or point `MOCKS_FILE` to your own file):

```yaml
- method: GET
  path: /users
  response:
    status: 200
    body:
      users:
        - id: 1
          name: Alice

- method: POST
  path: /users
  response:
    status: 201
    body:
      id: 2
      name: New User

- method: DELETE
  path: /users/*        # wildcard — matches /users/1, /users/42, etc.
  response:
    status: 204
    body: null
```

### Option 2 — Admin API at runtime

```bash
curl -X POST http://localhost:8000/admin/mocks \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "path": "/orders",
    "response": {
      "status": 200,
      "body": { "orders": [] }
    }
  }'
```

---

## Mock Definition Fields

| Field | Required | Description |
|---|---|---|
| `method` | yes | HTTP method: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `path` | yes | URL path. Supports `*` wildcards (e.g. `/users/*`) |
| `response.status` | no | HTTP status code. Default: `200` |
| `response.body` | no | JSON response body. Default: `null` |
| `response.headers` | no | Extra response headers. Default: `{}` |
| `response.delay_ms` | no | Artificial delay in milliseconds. Default: `0` |

**Note:** When multiple mocks match the same method + path, the **last registered one wins**. Use this to easily override mocks per test.

---

## Admin API Reference

### Mocks

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/admin/mocks` | Register a new mock |
| `GET` | `/admin/mocks` | List all registered mocks |
| `DELETE` | `/admin/mocks/{id}` | Remove a mock by id |
| `DELETE` | `/admin/mocks` | Remove all mocks |

### Request Log

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/requests` | Get all recorded requests |
| `DELETE` | `/admin/requests` | Clear the request log |

---

## Using in a Test Automation Framework

```python
import requests

BASE = "http://localhost:8000"


def setup_mock(method, path, status, body):
    requests.post(f"{BASE}/admin/mocks", json={
        "method": method,
        "path": path,
        "response": {"status": status, "body": body}
    })


def teardown():
    requests.delete(f"{BASE}/admin/mocks")
    requests.delete(f"{BASE}/admin/requests")


def get_recorded_requests():
    return requests.get(f"{BASE}/admin/requests").json()


# ── Example test ──────────────────────────────────────────────────────────────

def test_create_user():
    # Arrange
    setup_mock("POST", "/users", 201, {"id": 99, "name": "Test User"})

    # Act — call your service under test (which calls the mock server)
    response = requests.post(f"{BASE}/users", json={"name": "Test User"})

    # Assert response
    assert response.status_code == 201
    assert response.json()["id"] == 99

    # Assert the request was actually made
    calls = get_recorded_requests()
    assert any(r["method"] == "POST" and r["path"] == "/users" for r in calls)

    # Cleanup
    teardown()
```

### pytest fixture example

```python
import pytest
import requests

BASE = "http://localhost:8000"

@pytest.fixture(autouse=True)
def reset_mocks():
    yield
    requests.delete(f"{BASE}/admin/mocks")
    requests.delete(f"{BASE}/admin/requests")
```

---

## Simulating Edge Cases

```yaml
# Slow response
- method: GET
  path: /slow-endpoint
  response:
    status: 200
    body: { "message": "delayed" }
    delay_ms: 2000

# Server error
- method: GET
  path: /broken
  response:
    status: 500
    body: { "error": "Internal Server Error" }

# Custom headers
- method: GET
  path: /secure
  response:
    status: 200
    body: { "data": "secret" }
    headers:
      X-Auth-Token: abc123
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MOCKS_FILE` | `mocks/example.yaml` | Path to the YAML mock file loaded on startup |
| `PORT` | `5000` | Port the server listens on |

---

## Project Structure

```
├── server.py          # Flask app — catch-all route, startup
├── admin.py           # Admin API blueprint (/admin/*)
├── store.py           # In-memory mock store and request log
├── mocks/
│   └── example.yaml   # Pre-loaded mock definitions
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
