# Dummy REST API Servers

A collection of **4 dummy REST API servers** — 2 in **Python (FastAPI)** and 2 in **Java (Spring Boot)**.
Each server exposes **5 entities** with **GET (list)**, **GET by id**, **POST**, and **DELETE** operations,
backed by in-memory storage. Every server ships with **Swagger / OpenAPI** documentation and a **configurable port**.

## Overview

| # | Server | Stack | Default Port | Entities | Swagger UI |
|---|--------|-------|--------------|----------|------------|
| 1 | Bookstore | Python / FastAPI | `8001` | authors, publishers, categories, books, customers | http://localhost:8001/docs |
| 2 | Inventory | Python / FastAPI | `8002` | suppliers, warehouses, categories, products, orders | http://localhost:8002/docs |
| 3 | School | Java / Spring Boot | `8081` | students, teachers, courses, classrooms, enrollments | http://localhost:8081/swagger-ui.html |
| 4 | Hospital | Java / Spring Boot | `8082` | patients, doctors, departments, appointments, medications | http://localhost:8082/swagger-ui.html |

## Folder structure

```
DummyServers/
├── README.md                          <- this file
├── run-servers.bat                    <- selective launcher (Windows)
├── python-fastapi/
│   ├── bookstore-server/   (port 8001)
│   │   ├── main.py
│   │   ├── auth.py              <- API Key + JWT auth
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── inventory-server/   (port 8002)
│       ├── main.py
│       ├── auth.py
│       ├── requirements.txt
│       └── .env.example
├── java-springboot/
│   ├── school-server/      (port 8081)
│   │   ├── pom.xml
│   │   └── src/main/...     (incl. JwtService, AuthController, AuthFilter)
│   └── hospital-server/    (port 8082)
│       ├── pom.xml
│       └── src/main/...
└── Invoke/                             <- sample clients (see Invoke/README.md)
    ├── python/  (client.py, requirements.txt)
    └── java/    (InvokeClient.java)
```

## Quick start (Windows) — selective launcher

Use the included [run-servers.bat](run-servers.bat) to start any combination of servers, each in its own console window:

```bat
run-servers.bat            ::  interactive menu (pick which servers)
run-servers.bat 1          ::  start Bookstore only
run-servers.bat 1 3        ::  start Bookstore + School
run-servers.bat all        ::  start all four
```

Server numbers: `1`=Bookstore (8001), `2`=Inventory (8002), `3`=School (8081), `4`=Hospital (8082).
The script installs Python deps automatically and runs Maven for the Java servers.

## Common API shape

For every entity `<e>` on every server:

| Method | Path          | Description        |
|--------|---------------|--------------------|
| GET    | `/<e>`        | List all items     |
| GET    | `/<e>/{id}`   | Get one item by id |
| POST   | `/<e>`        | Create a new item  |
| DELETE | `/<e>/{id}`   | Delete by id       |

> Storage is in-memory, so data resets on restart. Each server is pre-seeded with 2 sample rows per entity.

---

## Authentication

Authentication is **optional** and controlled by the `AUTH_ENABLED` config flag (default `true`).

- `AUTH_ENABLED=true` (default) → every entity endpoint requires an API key **or** a JWT.
- `AUTH_ENABLED=false` → the API runs completely open; **no** key/token is needed and the clients
  send no auth headers (use `none` mode).

```powershell
# Windows PowerShell — run a FastAPI server WITHOUT auth
$env:AUTH_ENABLED="false"; python main.py

# A Spring Boot server WITHOUT auth
$env:AUTH_ENABLED="false"; mvn spring-boot:run
```

When enabled, send one of these headers on each request:

| Type | Header | Example |
|------|--------|---------|
| **API Key** | `X-API-Key` | `X-API-Key: my-secret-api-key` |
| **JWT** (Bearer) | `Authorization` | `Authorization: Bearer <token>` |

Get a JWT from the public login endpoint (no auth needed) on any server:

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
# -> { "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 }
```

The `/auth/login` endpoint, the root `/`, and the Swagger UI are public; everything else requires auth.
In **Swagger UI**, click **Authorize** and supply either the API key or a Bearer token to try endpoints.

### Default credentials & configuration

| Setting | Default | Env var |
|---------|---------|---------|
| Auth on/off | `true` | `AUTH_ENABLED` |
| API key | `my-secret-api-key` | `API_KEY` |
| Login user | `admin` | `AUTH_USER` |
| Login password | `password` | `AUTH_PASS` |
| JWT secret | (built-in dev secret) | `JWT_SECRET` |
| JWT expiry (seconds) | `3600` | `JWT_EXP_SECONDS` |

Set these via environment variables before starting a server (FastAPI reads them directly; Spring Boot
maps them in `application.properties`). For example on Windows PowerShell:

```powershell
$env:API_KEY="prod-key"; $env:AUTH_PASS="s3cret"; python main.py
```

---

## Python FastAPI servers

### Prerequisites
- Python 3.9+

### Run the Bookstore server (port 8001)

```bash
cd python-fastapi/bookstore-server
python -m venv venv
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# macOS / Linux:
# source venv/bin/activate

pip install -r requirements.txt
python main.py
```

### Run the Inventory server (port 8002)

```bash
cd python-fastapi/inventory-server
python -m venv venv
venv\Scripts\Activate.ps1        # or: source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Changing the port (FastAPI)

The port is read from the `PORT` environment variable (defaults: 8001 / 8002).

```bash
# Windows PowerShell
$env:PORT=9001; python main.py

# macOS / Linux
PORT=9001 python main.py
```

You can also run via uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 9001
```

### FastAPI documentation links
- Bookstore Swagger UI: http://localhost:8001/docs  · ReDoc: http://localhost:8001/redoc  · OpenAPI JSON: http://localhost:8001/openapi.json
- Inventory Swagger UI: http://localhost:8002/docs  · ReDoc: http://localhost:8002/redoc  · OpenAPI JSON: http://localhost:8002/openapi.json

---

## Java Spring Boot servers

### Prerequisites
- Java 17+
- Maven 3.9+ (or use the `mvn` available on your PATH)

### Run the School server (port 8081)

```bash
cd java-springboot/school-server
mvn spring-boot:run
```

### Run the Hospital server (port 8082)

```bash
cd java-springboot/hospital-server
mvn spring-boot:run
```

Or build a jar and run it:

```bash
mvn clean package
java -jar target/school-server-1.0.0.jar
```

### Changing the port (Spring Boot)

The port is defined in `src/main/resources/application.properties` as
`server.port=${SERVER_PORT:8081}`. Override it any of these ways:

```bash
# Command-line argument
mvn spring-boot:run -Dspring-boot.run.arguments=--server.port=9081
java -jar target/school-server-1.0.0.jar --server.port=9081

# Environment variable
# Windows PowerShell
$env:SERVER_PORT=9081; mvn spring-boot:run
# macOS / Linux
SERVER_PORT=9081 mvn spring-boot:run
```

### Spring Boot documentation links
- School Swagger UI: http://localhost:8081/swagger-ui.html  · OpenAPI JSON: http://localhost:8081/v3/api-docs
- Hospital Swagger UI: http://localhost:8082/swagger-ui.html  · OpenAPI JSON: http://localhost:8082/v3/api-docs

---

## Quick test (curl)

Every entity request must carry an API key **or** a Bearer token (see [Authentication](#authentication)).

```bash
# --- Using an API key (FastAPI) ---
curl http://localhost:8001/books -H "X-API-Key: my-secret-api-key"

curl -X POST http://localhost:8001/books \
  -H "X-API-Key: my-secret-api-key" -H "Content-Type: application/json" \
  -d '{"title":"New Book","author_id":1,"price":15.0}'

curl -X DELETE http://localhost:8001/books/1 -H "X-API-Key: my-secret-api-key"

# --- Using a JWT (Spring Boot) ---
TOKEN=$(curl -s -X POST http://localhost:8081/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | sed -E 's/.*"access_token":"([^"]+)".*/\1/')

curl http://localhost:8081/students -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8081/students \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"New Student","age":15,"grade":"10"}'

curl -X DELETE http://localhost:8081/students/1 -H "Authorization: Bearer $TOKEN"
```

## Invoke — sample clients

The [Invoke/](Invoke/) folder has ready-to-run clients (Python and Java) that exercise the full
CRUD cycle against every server using either auth type. See [Invoke/README.md](Invoke/README.md).

```bash
# Python
cd Invoke/python && pip install -r requirements.txt
python client.py            # all servers, API key
python client.py jwt        # all servers, JWT
python client.py none       # all servers, NO auth (server must have AUTH_ENABLED=false)

# Java (single file, Java 11+)
cd Invoke/java
java InvokeClient.java       # all servers, API key
java InvokeClient.java jwt   # all servers, JWT
java InvokeClient.java none  # all servers, NO auth
```

> The clients also auto-pick `none` if `AUTH_ENABLED=false` is set in their environment.

## Notes
- All four servers can run at the same time since they use different default ports.
- No database is required — data lives in memory and is reset on restart.
- Swagger UI lets you exercise every endpoint interactively from the browser.
