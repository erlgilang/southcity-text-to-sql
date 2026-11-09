import httpx
import pytest
from api_client import ApiClient, ApiError, SessionExpiredError


def client_with(handler):
    return ApiClient("http://api.test", transport=httpx.MockTransport(handler))


def test_list_users_returns_the_json_body():
    users = [{"username": "a", "full_name": "A", "role": "Sales"}]
    client = client_with(lambda request: httpx.Response(200, json=users))
    assert client.list_users() == users


def test_create_session_posts_the_username():
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, request.read()))
        return httpx.Response(200, json={"session_id": "s1", "user": {}})

    assert client_with(handler).create_session("sales_dewi")["session_id"] == "s1"
    assert seen == [("POST", "/sessions", b'{"username":"sales_dewi"}')]


def test_chat_sends_session_and_question():
    seen = []

    def handler(request):
        seen.append(request.read())
        return httpx.Response(200, json={"answer": "ok"})

    assert client_with(handler).chat("s1", "Halo")["answer"] == "ok"
    assert seen == [b'{"session_id":"s1","question":"Halo"}']


def test_missing_session_is_reported_as_expired():
    client = client_with(lambda request: httpx.Response(404, json={"detail": "x"}))
    with pytest.raises(SessionExpiredError):
        client.chat("gone", "Halo")


def test_unknown_user_on_session_creation_is_a_normal_error():
    client = client_with(
        lambda request: httpx.Response(404, json={"detail": "User tidak ditemukan."})
    )
    with pytest.raises(ApiError, match=r"User tidak ditemukan."):
        client.create_session("root")


def test_message_limit_shows_the_server_text():
    client = client_with(
        lambda request: httpx.Response(429, json={"detail": "Batas pesan tercapai."})
    )
    with pytest.raises(ApiError, match=r"Batas pesan tercapai."):
        client.chat("s1", "x")


def test_validation_error_gets_a_readable_message():
    client = client_with(
        lambda request: httpx.Response(422, json={"detail": [{"msg": "too long"}]})
    )
    with pytest.raises(ApiError, match="1 sampai 500 karakter"):
        client.chat("s1", "x")


def test_server_error_without_json_mentions_the_status_code():
    client = client_with(lambda request: httpx.Response(502, text="bad gateway"))
    with pytest.raises(ApiError, match="502"):
        client.chat("s1", "x")


def test_unreachable_api_says_what_to_check():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ApiError, match="API_BASE_URL"):
        client_with(handler).list_users()


def test_timeout_asks_to_retry():
    def handler(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(ApiError, match="terlalu lama"):
        client_with(handler).chat("s1", "x")
