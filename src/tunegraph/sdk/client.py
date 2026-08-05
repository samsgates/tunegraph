from __future__ import annotations

from typing import Any

import httpx


class TuneGraphClient:
    """Small synchronous SDK for automation and examples."""

    def __init__(
        self,
        base_url: str,
        *,
        access_token: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        headers: dict[str, str] = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TuneGraphClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def login(
        self,
        email: str,
        password: str,
        *,
        organization_slug: str = "default",
    ) -> dict[str, Any]:
        response = self._client.post(
            "/api/v1/auth/login",
            json={
                "organization_slug": organization_slug,
                "email": email,
                "password": password,
            },
        )
        response.raise_for_status()
        data = response.json()
        self._client.headers["Authorization"] = f"Bearer {data['access_token']}"
        return data

    def create_base_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/base-models", json=payload)

    def create_dataset(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/datasets", json=payload)

    def create_capability(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/capabilities", json=payload)

    def create_patch(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/patches", json=payload)

    def create_graph(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/graphs", json=payload)

    def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/chat/completions", json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()
