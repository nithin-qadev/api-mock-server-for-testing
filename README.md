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

## Using in a Java REST Assured + TestNG Framework

### build.gradle

```groovy
plugins {
    id 'java'
}

repositories {
    mavenCentral()
}

dependencies {
    testImplementation 'io.rest-assured:rest-assured:5.4.0'
    testImplementation 'org.testng:testng:7.9.0'
    testImplementation 'org.hamcrest:hamcrest:2.2'
}

test {
    useTestNG()
}
```

### Base test class (reuse across all tests)

```java
import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeSuite;

import static io.restassured.RestAssured.given;

public abstract class MockServerTest {

    protected static final String MOCK_SERVER = "http://localhost:8000";

    @BeforeSuite
    public void configure() {
        RestAssured.baseURI = MOCK_SERVER;
    }

    // Register a mock before each test
    protected void registerMock(String method, String path, int status, String bodyJson) {
        String payload = String.format("""
            {
                "method": "%s",
                "path": "%s",
                "response": {
                    "status": %d,
                    "body": %s
                }
            }
        """, method, path, status, bodyJson);

        given()
            .contentType(ContentType.JSON)
            .body(payload)
        .when()
            .post("/admin/mocks")
        .then()
            .statusCode(201);
    }

    // Wipe mocks and request log after every test
    @AfterMethod
    public void resetMockServer() {
        given().delete("/admin/mocks").then().statusCode(204);
        given().delete("/admin/requests").then().statusCode(204);
    }
}
```

### Example tests

```java
import org.testng.Assert;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.util.List;
import java.util.Map;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

public class UserApiTest extends MockServerTest {

    @BeforeMethod
    public void setupMocks() {
        registerMock("GET", "/users", 200, """
            { "users": [{ "id": 1, "name": "Alice" }] }
        """);

        registerMock("POST", "/users", 201, """
            { "id": 99, "name": "New User" }
        """);

        registerMock("PUT", "/users/*", 200, """
            { "id": 1, "name": "Updated User" }
        """);

        registerMock("PATCH", "/users/*", 200, """
            { "id": 1, "name": "Patched User" }
        """);

        registerMock("DELETE", "/users/*", 204, "null");
    }

    @Test
    public void shouldReturnUsersList() {
        given()
        .when()
            .get("/users")
        .then()
            .statusCode(200)
            .body("users.size()", equalTo(1))
            .body("users[0].name", equalTo("Alice"));
    }

    @Test
    public void shouldCreateUser() {
        given()
            .contentType("application/json")
            .body("{ \"name\": \"New User\" }")
        .when()
            .post("/users")
        .then()
            .statusCode(201)
            .body("id", equalTo(99));
    }

    @Test
    public void shouldFullyUpdateUser() {
        given()
            .contentType("application/json")
            .body("{ \"name\": \"Updated User\" }")
        .when()
            .put("/users/1")
        .then()
            .statusCode(200)
            .body("name", equalTo("Updated User"));
    }

    @Test
    public void shouldPartiallyUpdateUser() {
        given()
            .contentType("application/json")
            .body("{ \"name\": \"Patched User\" }")
        .when()
            .patch("/users/1")
        .then()
            .statusCode(200)
            .body("name", equalTo("Patched User"));
    }

    @Test
    public void shouldDeleteUser() {
        given()
        .when()
            .delete("/users/1")
        .then()
            .statusCode(204);
    }

    @Test
    public void shouldVerifyRequestWasMade() {
        // Act
        given().contentType("application/json").body("{}").post("/users");

        // Assert — check the mock server received the call
        List<Map<String, Object>> requests =
            given().get("/admin/requests").jsonPath().getList("$");

        boolean found = requests.stream().anyMatch(r ->
            "POST".equals(r.get("method")) && "/users".equals(r.get("path"))
        );
        Assert.assertTrue(found, "Expected POST /users to be recorded");
    }
}
```

### Simulating errors in a test

```java
@Test
public void shouldHandleServerError() {
    registerMock("GET", "/users", 500, """
        { "error": "Internal Server Error" }
    """);

    given()
    .when()
        .get("/users")
    .then()
        .statusCode(500)
        .body("error", equalTo("Internal Server Error"));
}

@Test
public void shouldHandleUnauthorized() {
    registerMock("GET", "/users", 401, """
        { "error": "Unauthorized" }
    """);

    given()
    .when()
        .get("/users")
    .then()
        .statusCode(401)
        .body("error", equalTo("Unauthorized"));
}
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
| `PORT` | `8000` | Port the server listens on |

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
