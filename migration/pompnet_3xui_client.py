"""Pinned 3X-UI v3.11.0 HTTP client for the POMP NET migration adapter.

This module is deliberately not wired into the production startup yet. It uses
only the documented v3.11.0 /panel/api/clients contract and keeps credentials
server-side. It does not migrate or mutate legacy Marzban data by itself.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping


class ThreeXUIError(RuntimeError):
    pass


class ThreeXUIClient:
    """Small stdlib-only client for MHSanaei/3x-ui v3.11.0."""

    API_PREFIX = "/panel/api/clients"

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        api_token: str | None = None,
        timeout: float = 15.0,
        opener: Any | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("XUI_BASE_URL", "")).rstrip("/")
        self.username = username or os.getenv("XUI_USERNAME", "")
        self.password = password or os.getenv("XUI_PASSWORD", "")
        self.api_token = api_token or os.getenv("XUI_API_TOKEN", "")
        self.timeout = timeout
        self._csrf_token = ""
        if opener is None:
            jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(jar)
            )
        self._opener = opener
        if not self.base_url:
            raise ThreeXUIError("XUI_BASE_URL is required")

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        url = self.base_url + path
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        if authenticated and self.api_token:
            headers["Authorization"] = "Bearer " + self.api_token
        elif authenticated and self._csrf_token:
            headers["X-CSRF-Token"] = self._csrf_token
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise ThreeXUIError(f"3X-UI HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ThreeXUIError(f"3X-UI connection failed: {exc}") from exc
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise ThreeXUIError("3X-UI returned non-JSON data") from exc
        if isinstance(data, dict):
            if data.get("success") is False or (
                "success" not in data and data.get("msg") and data.get("obj") is None
                and data.get("status") == "error"
            ):
                raise ThreeXUIError(str(data.get("msg") or "3X-UI API request failed"))
        return data

    @staticmethod
    def _obj(response: Any) -> Any:
        if isinstance(response, dict) and "obj" in response:
            return response["obj"]
        return response

    def login(self) -> None:
        if self.api_token:
            return
        if not self.username or not self.password:
            raise ThreeXUIError("Set XUI_API_TOKEN or XUI_USERNAME and XUI_PASSWORD")
        # v3.11.0 protects session-authenticated API writes with a CSRF token.
        try:
            csrf = self._request("GET", "/panel/csrf-token", authenticated=False)
            if isinstance(csrf, dict):
                self._csrf_token = str(
                    csrf.get("token") or csrf.get("csrfToken") or
                    (csrf.get("obj") or {}).get("token", "")
                )
        except ThreeXUIError:
            # Some deployments disable CSRF or use a bearer API token.
            self._csrf_token = ""
        result = self._request(
            "POST", "/login",
            {"username": self.username, "password": self.password},
            authenticated=False,
        )
        if isinstance(result, dict) and result.get("success") is False:
            raise ThreeXUIError(str(result.get("msg") or "3X-UI login failed"))
        # Refresh CSRF after login because the session cookie may have changed.
        if not self._csrf_token:
            try:
                csrf = self._request("GET", "/panel/csrf-token", authenticated=False)
                if isinstance(csrf, dict):
                    self._csrf_token = str(
                        csrf.get("token") or csrf.get("csrfToken") or
                        (csrf.get("obj") or {}).get("token", "")
                    )
            except ThreeXUIError:
                pass

    def _call(self, method: str, suffix: str, payload: Mapping[str, Any] | None = None) -> Any:
        return self._request(method, self.API_PREFIX + suffix, payload)

    def list_clients(self) -> Any:
        return self._obj(self._call("GET", "/list"))

    def get_client(self, email: str) -> Any:
        return self._obj(self._call("GET", "/get/" + urllib.parse.quote(email, safe="")))

    def add_client(self, payload: Mapping[str, Any]) -> Any:
        # Payload is the native v3.11.0 client object; callers must validate it.
        return self._obj(self._call("POST", "/add", payload))

    def update_client(self, email: str, payload: Mapping[str, Any]) -> Any:
        # v3 update replaces the full client row; caller must send all retained fields.
        return self._obj(self._call(
            "POST", "/update/" + urllib.parse.quote(email, safe=""), payload
        ))

    def delete_client(self, email: str, keep_traffic: bool = False) -> Any:
        query = "?keepTraffic=1" if keep_traffic else ""
        return self._obj(self._call(
            "POST", "/del/" + urllib.parse.quote(email, safe="") + query
        ))

    def get_traffic(self, email: str) -> Any:
        return self._obj(self._call(
            "GET", "/traffic/" + urllib.parse.quote(email, safe="")
        ))

    def get_subscription_links(self, sub_id: str) -> Any:
        return self._obj(self._call(
            "GET", "/subLinks/" + urllib.parse.quote(sub_id, safe="")
        ))
