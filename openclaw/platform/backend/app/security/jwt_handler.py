"""Minimal, dependency-free HS256 JWT encode/decode.

Implemented with the standard library so the platform runs without PyJWT. The API
mirrors what services need: ``encode(claims)`` and ``decode(token)`` (which raises
``JwtError`` on any tampering or expiry).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class JwtError(Exception):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


class JwtHandler:
    def __init__(self, secret: str, algorithm: str = "HS256",
                 expire_minutes: int = 720) -> None:
        if algorithm != "HS256":
            raise ValueError("Only HS256 is supported by this handler.")
        self._secret = secret.encode("utf-8")
        self._algorithm = algorithm
        self._expire_seconds = expire_minutes * 60

    def _sign(self, signing_input: bytes) -> str:
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return _b64url(sig)

    def encode(self, claims: dict[str, Any]) -> str:
        now = int(time.time())
        payload = {"iat": now, "exp": now + self._expire_seconds, **claims}
        header = {"alg": self._algorithm, "typ": "JWT"}
        h = _b64url(json.dumps(header, separators=(",", ":")).encode())
        p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{h}.{p}".encode()
        return f"{h}.{p}.{self._sign(signing_input)}"

    def decode(self, token: str) -> dict[str, Any]:
        try:
            h, p, sig = token.split(".")
        except ValueError as exc:
            raise JwtError("Malformed token") from exc
        expected = self._sign(f"{h}.{p}".encode())
        if not hmac.compare_digest(sig, expected):
            raise JwtError("Invalid signature")
        try:
            payload = json.loads(_b64url_decode(p))
        except Exception as exc:  # noqa: BLE001
            raise JwtError("Invalid payload") from exc
        if "exp" in payload and int(time.time()) > int(payload["exp"]):
            raise JwtError("Token expired")
        return payload
