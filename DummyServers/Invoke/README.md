# Invoke — Clients for the Dummy Servers

Sample clients that call all four dummy servers using any auth mode:
**API Key**, **JWT**, or **none** (when the servers run with `AUTH_ENABLED=false`).
Start the servers first (see the root [README](../README.md) or `run-servers.bat`).

Auth mode is chosen by argument, or defaults from the environment: `AUTH_MODE` if set,
otherwise `none` when `AUTH_ENABLED=false`, otherwise `apikey`.

## Python client

```bash
cd Invoke/python
pip install -r requirements.txt

python client.py                 # demo all 4 servers with API key
python client.py jwt             # demo all 4 servers with JWT
python client.py none            # demo all 4 servers with NO auth
python client.py bookstore       # one server, API key
python client.py school jwt      # one server, JWT
```

## Java client (single file, Java 11+, no build required)

```bash
cd Invoke/java

java InvokeClient.java                 # demo all 4 servers with API key
java InvokeClient.java jwt             # demo all 4 servers with JWT
java InvokeClient.java none            # demo all 4 servers with NO auth
java InvokeClient.java bookstore jwt   # one server, JWT
```

Each client performs a full **GET (list) → POST → GET by id → DELETE** cycle per server.
If a server isn't running, that server is skipped with a message.

## Default credentials / keys
| Setting | Value |
|---------|-------|
| API key (`X-API-Key`) | `my-secret-api-key` |
| Login user / pass (for JWT via `POST /auth/login`) | `admin` / `password` |

These are configurable per server via environment variables — see the root README.
