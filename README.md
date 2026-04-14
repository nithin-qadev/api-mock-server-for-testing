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

## Stateful User CRUD

A real in-memory user store pre-populated with 3 users on every startup. Data resets on server restart — ideal for repeatable test runs.

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/users` | List all users |
| `POST` | `/users` | Create a user (id auto-assigned) |
| `GET` | `/users/{id}` | Get a single user |
| `PUT` | `/users/{id}` | Full replace — entire object is replaced |
| `PATCH` | `/users/{id}` | Partial update — only sent fields are changed |
| `DELETE` | `/users/{id}` | Delete a user |

Returns `404` with `{ "error": "User {id} not found" }` when the user doesn't exist.

### Seed user structure

Each user covers a variety of data types for thorough assertion testing:

```json
{
  "id": 1,
  "name": "Alice Nguyen",
  "email": "alice@example.com",
  "age": 34,
  "active": true,
  "score": 97.4,
  "phone": "+1-555-0101",
  "address": {
    "street": "12 Maple Avenue",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94103",
    "country": "US"
  },
  "tags": ["admin", "qa-lead", "automation"],
  "lucky_numbers": [3, 7, 21, 42],
  "ratings": [4.8, 4.9, 5.0, 4.7],
  "preferences": {
    "theme": "dark",
    "language": "en",
    "notifications": true,
    "timezone": "America/Los_Angeles"
  },
  "roles": [
    { "id": 1, "name": "admin",   "level": 5, "permissions": ["read", "write", "delete"] },
    { "id": 2, "name": "qa-lead", "level": 4, "permissions": ["read", "write"] }
  ],
  "login_history": [
    { "timestamp": "2026-04-01T09:00:00Z", "ip": "192.168.1.10", "success": true },
    { "timestamp": "2026-04-10T14:23:00Z", "ip": "192.168.1.10", "success": true }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `id`, `age` | int | |
| `score` | float | |
| `active` | boolean | User 3 is inactive (`false`) |
| `phone` | string / null | User 2 has `null` phone |
| `address`, `preferences` | nested object | |
| `tags` | list of strings | |
| `lucky_numbers` | list of ints | |
| `ratings` | list of floats | |
| `roles` | array of objects | each has a `permissions` list of strings |
| `login_history` | array of objects | User 2 has a failed login attempt |

### Java REST Assured examples

```java
@Test
public void shouldListAllUsers() {
    given()
    .when()
        .get("/users")
    .then()
        .statusCode(200)
        .body("size()", equalTo(3));
}

@Test
public void shouldGetUserById() {
    given()
    .when()
        .get("/users/1")
    .then()
        .statusCode(200)
        .body("name", equalTo("Alice Nguyen"))
        .body("active", equalTo(true))
        .body("score", equalTo(97.4f))
        .body("address.city", equalTo("San Francisco"))
        .body("tags", hasItems("admin", "qa-lead"))
        .body("lucky_numbers", hasItems(3, 7, 21, 42))
        .body("roles[0].name", equalTo("admin"))
        .body("roles[0].permissions", hasItems("read", "write", "delete"))
        .body("login_history.size()", equalTo(2));
}

@Test
public void shouldReturnNullPhoneForUser2() {
    given()
    .when()
        .get("/users/2")
    .then()
        .statusCode(200)
        .body("phone", nullValue());
}

@Test
public void shouldCreateUser() {
    String body = """
        {
          "name": "Dave Lee",
          "email": "dave@example.com",
          "age": 25,
          "active": true,
          "tags": ["tester"],
          "roles": [{ "id": 5, "name": "viewer", "level": 1, "permissions": ["read"] }]
        }
    """;

    given()
        .contentType("application/json")
        .body(body)
    .when()
        .post("/users")
    .then()
        .statusCode(201)
        .body("id", equalTo(4))
        .body("name", equalTo("Dave Lee"));
}

@Test
public void shouldFullyReplaceUser() {
    String body = """
        { "name": "Alice Updated", "email": "alice-new@example.com", "age": 35, "active": false }
    """;

    given()
        .contentType("application/json")
        .body(body)
    .when()
        .put("/users/1")
    .then()
        .statusCode(200)
        .body("name", equalTo("Alice Updated"))
        .body("age", equalTo(35));
}

@Test
public void shouldPartiallyUpdateUser() {
    given()
        .contentType("application/json")
        .body("{ \"active\": false }")
    .when()
        .patch("/users/2")
    .then()
        .statusCode(200)
        .body("active", equalTo(false))
        .body("name", equalTo("Bob Martinez"));   // unchanged
}

@Test
public void shouldDeleteUser() {
    given().delete("/users/3").then().statusCode(204);
    given().get("/users/3").then().statusCode(404);
}

@Test
public void shouldReturn404ForMissingUser() {
    given().get("/users/999").then().statusCode(404);
}
```

---

## Built-in Dynamic Endpoints

These are built-in routes with dynamic behaviour — not configurable via YAML.

---

### Echo — `POST /echo`

Returns the request body unchanged, with a `timestamp` field added.

**Request**
```json
POST /echo
{
  "name": "Alice",
  "role": "admin"
}
```

**Response `200`**
```json
{
  "name": "Alice",
  "role": "admin",
  "timestamp": "2026-04-13T10:30:00.000000+00:00"
}
```

---

### Authenticated Echo — `POST /echo/secure`

Same as `/echo` but requires a valid Bearer token. Returns `401` if the token is missing, malformed, or expired.

**Request**
```
POST /echo/secure
Authorization: Bearer a3f1c2d4-...

{ "name": "Alice" }
```

**Response `200` — valid token**
```json
{
  "name": "Alice",
  "timestamp": "2026-04-13T10:30:00.000000+00:00"
}
```

**Response `401` — invalid or expired token**
```json
{ "valid": false, "error": "Token is invalid or expired" }
```

---

### Get Token — `POST /auth/token`

Issues a token valid for **30 minutes**.

**Request**
```
POST /auth/token
```

**Response `201`**
```json
{
  "token": "a3f1c2d4-...",
  "expires_at": "2026-04-13T11:00:00.000000+00:00",
  "expires_in": 1800
}
```

---

### Validate Token — `GET /auth/validate`

Validates the Bearer token from the `Authorization` header.

**Request**
```
GET /auth/validate
Authorization: Bearer a3f1c2d4-...
```

**Response `200` — valid token**
```json
{ "valid": true, "message": "Token is valid" }
```

**Response `401` — invalid or expired**
```json
{ "valid": false, "error": "Token is invalid or expired" }
```

**Response `401` — missing header**
```json
{ "valid": false, "error": "Missing or malformed Authorization header. Expected: Bearer <token>" }
```

---

### Java REST Assured examples

```java
@Test
public void shouldEchoRequestBodyWithTimestamp() {
    given()
        .contentType("application/json")
        .body("{ \"name\": \"Alice\", \"role\": \"admin\" }")
    .when()
        .post("/echo")
    .then()
        .statusCode(200)
        .body("name", equalTo("Alice"))
        .body("role", equalTo("admin"))
        .body("timestamp", notNullValue());
}

@Test
public void shouldIssueAndValidateToken() {
    // Step 1 — get a token
    String token =
        given()
        .when()
            .post("/auth/token")
        .then()
            .statusCode(201)
            .body("token", notNullValue())
            .body("expires_in", equalTo(1800))
            .extract().path("token");

    // Step 2 — use the token to validate
    given()
        .header("Authorization", "Bearer " + token)
    .when()
        .get("/auth/validate")
    .then()
        .statusCode(200)
        .body("valid", equalTo(true));
}

@Test
public void shouldRejectMissingToken() {
    given()
    .when()
        .get("/auth/validate")
    .then()
        .statusCode(401)
        .body("valid", equalTo(false));
}

@Test
public void shouldEchoWithValidToken() {
    // Step 1 — get a token
    String token =
        given()
        .when()
            .post("/auth/token")
        .then()
            .statusCode(201)
            .extract().path("token");

    // Step 2 — call authenticated echo
    given()
        .contentType("application/json")
        .header("Authorization", "Bearer " + token)
        .body("{ \"name\": \"Alice\" }")
    .when()
        .post("/echo/secure")
    .then()
        .statusCode(200)
        .body("name", equalTo("Alice"))
        .body("timestamp", notNullValue());
}

@Test
public void shouldRejectAuthenticatedEchoWithoutToken() {
    given()
        .contentType("application/json")
        .body("{ \"name\": \"Alice\" }")
    .when()
        .post("/echo/secure")
    .then()
        .statusCode(401)
        .body("valid", equalTo(false));
}

@Test
public void shouldRejectInvalidToken() {
    given()
        .header("Authorization", "Bearer not-a-real-token")
    .when()
        .get("/auth/validate")
    .then()
        .statusCode(401)
        .body("valid", equalTo(false));
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
├── dynamic.py         # Built-in dynamic routes (/echo, /auth/*)
├── resources.py       # Stateful user CRUD (/users) + seed data
├── store.py           # In-memory store: mocks, request log, tokens, users
├── mocks/
│   └── example.yaml   # Pre-loaded mock definitions
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
