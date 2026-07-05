"""
Python client for the Dummy REST API servers.

Supports three auth modes (matching the server's optional auth config):
  * apikey -> sent as the "X-API-Key" header
  * jwt    -> obtained from POST /auth/login, sent as "Authorization: Bearer <token>"
  * none   -> no auth header (use when the server runs with AUTH_ENABLED=false)

Usage:
    python client.py                 # demo all 4 servers (auth mode from AUTH_MODE env, default apikey)
    python client.py none            # demo all 4 servers with NO auth
    python client.py bookstore       # demo a single server
    python client.py school jwt      # force JWT auth for one server

Requires: pip install -r requirements.txt
"""
import os
import sys

import requests

API_KEY = os.getenv("API_KEY", "my-secret-api-key")
USERNAME = os.getenv("AUTH_USER", "admin")
PASSWORD = os.getenv("AUTH_PASS", "password")
# Default auth mode: AUTH_MODE wins; else "none" if AUTH_ENABLED=false; else "apikey".
DEFAULT_AUTH = os.getenv(
    "AUTH_MODE",
    "none" if os.getenv("AUTH_ENABLED", "true").strip().lower() in ("0", "false", "no", "off") else "apikey",
)

# server name -> (base_url, sample entity, sample POST body)
SERVERS = {
    "bookstore": ("http://localhost:8001", "books",
                  {"title": "Client Test Book", "author_id": 1, "price": 19.5}),
    "inventory": ("http://localhost:8002", "products",
                  {"name": "Client Test Product", "sku": "CT-001", "price": 12.0, "stock": 10}),
    "school":    ("http://localhost:8081", "students",
                  {"name": "Client Test Student", "age": 14, "grade": "9"}),
    "hospital":  ("http://localhost:8082", "patients",
                  {"name": "Client Test Patient", "age": 30, "bloodGroup": "B+"}),
}


class DummyApiClient:
    """A small REST client that can authenticate with an API key OR a JWT."""

    def __init__(self, base_url: str, auth: str = "apikey"):
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.session = requests.Session()

    def _headers(self) -> dict:
        if self.auth == "none":
            return {}
        if self.auth == "jwt":
            token = self.login()
            return {"Authorization": f"Bearer {token}"}
        return {"X-API-Key": API_KEY}

    def login(self) -> str:
        resp = self.session.post(
            f"{self.base_url}/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def list(self, entity: str):
        r = self.session.get(f"{self.base_url}/{entity}", headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def get(self, entity: str, item_id):
        r = self.session.get(f"{self.base_url}/{entity}/{item_id}", headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def create(self, entity: str, body: dict):
        r = self.session.post(f"{self.base_url}/{entity}", json=body, headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def delete(self, entity: str, item_id):
        r = self.session.delete(f"{self.base_url}/{entity}/{item_id}", headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()


def demo(name: str, auth: str) -> None:
    base_url, entity, body = SERVERS[name]
    print(f"\n=== {name.upper()}  ({base_url})  auth={auth} ===")
    client = DummyApiClient(base_url, auth=auth)
    try:
        items = client.list(entity)
        print(f"GET  /{entity}        -> {len(items)} item(s)")

        created = client.create(entity, body)
        new_id = created["id"]
        print(f"POST /{entity}        -> created id={new_id}")

        fetched = client.get(entity, new_id)
        print(f"GET  /{entity}/{new_id}      -> {fetched}")

        deleted = client.delete(entity, new_id)
        print(f"DEL  /{entity}/{new_id}      -> {deleted}")
    except requests.exceptions.ConnectionError:
        print(f"  [skipped] {name} server not reachable at {base_url}")
    except requests.exceptions.HTTPError as e:
        print(f"  [error] {e} :: {e.response.text}")


def main() -> None:
    args = sys.argv[1:]
    auth = DEFAULT_AUTH
    targets = list(SERVERS.keys())

    for a in args:
        if a in ("apikey", "jwt", "none"):
            auth = a
        elif a in SERVERS:
            targets = [a]
        else:
            print(f"Unknown argument: {a}")
            print(f"Servers: {', '.join(SERVERS)} | Auth: apikey, jwt, none")
            return

    for name in targets:
        demo(name, auth)


if __name__ == "__main__":
    main()
