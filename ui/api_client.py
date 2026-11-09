from typing import Any

import httpx

# A chat call can take 3 attempts of LLM and database work
TIMEOUT_SECONDS = 90.0


class ApiError(Exception):
    """An error with a message that is safe and useful to show to the user."""


class SessionExpiredError(ApiError):
    pass


class ApiClient:
    def __init__(self, base_url: str, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(base_url=base_url, timeout=TIMEOUT_SECONDS, transport=transport)

    def list_users(self) -> list[dict[str, Any]]:
        return self._request("GET", "/users")

    def create_session(self, username: str) -> dict[str, Any]:
        return self._request("POST", "/sessions", json={"username": username})

    def chat(self, session_id: str, question: str) -> dict[str, Any]:
        return self._request("POST", "/chat", json={"session_id": session_id, "question": question})

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.ConnectError as error:
            raise ApiError(
                "Server API tidak dapat dihubungi. Periksa bahwa API berjalan dan API_BASE_URL "
                "benar, lalu muat ulang halaman."
            ) from error
        except httpx.TimeoutException as error:
            raise ApiError(
                "Server terlalu lama menjawab. Kirim ulang pertanyaan, atau buat pertanyaan "
                "lebih spesifik."
            ) from error
        if response.is_success:
            return response.json()
        if response.status_code == 404 and path == "/chat":
            raise SessionExpiredError("Sesi berakhir.")
        if response.status_code == 422:
            raise ApiError(
                "Pertanyaan tidak dapat diproses. Panjangnya harus 1 sampai 500 karakter."
            )
        raise ApiError(_detail(response))


def _detail(response: httpx.Response) -> str:
    try:
        return response.json()["detail"]
    except (ValueError, KeyError):
        return f"Server membalas dengan kode {response.status_code}. Coba lagi beberapa saat lagi."
