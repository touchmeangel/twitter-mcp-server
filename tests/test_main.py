"""Unit tests for Twitter MCP server."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from main import (
    AuthContext,
    AuthMiddleware,
    get_auth_context,
    get_profile,
    get_tweets,
    get_xquik_api_key,
    like_tweet,
    post_tweet,
    search_tweets,
    set_auth_context,
    should_use_xquik_search,
    xquik_auth_headers,
)

# ============================================================================
# Auth Context Tests (Pure Logic - No External Dependencies)
# ============================================================================


def test_auth_context_set_and_get():
    """Test setting and getting auth context."""
    auth = AuthContext(auth_token="test_token", ct0="test_ct0")
    set_auth_context(auth)

    retrieved = get_auth_context()
    assert retrieved is not None
    assert retrieved.auth_token == "test_token"
    assert retrieved.ct0 == "test_ct0"


def test_auth_context_none_by_default():
    """Test auth context is None when not set."""
    set_auth_context(None)
    assert get_auth_context() is None


def test_xquik_search_backend_selection(monkeypatch):
    """Test Hermes Tweet search backend selection rules."""
    monkeypatch.delenv("HERMES_TWEET_API_KEY", raising=False)
    monkeypatch.delenv("XQUIK_API_KEY", raising=False)
    monkeypatch.delenv("X_READ_BACKEND", raising=False)

    assert get_xquik_api_key() is None
    assert should_use_xquik_search(None) is False

    monkeypatch.setenv("XQUIK_API_KEY", "xq_test")

    assert get_xquik_api_key() == "xq_test"
    assert should_use_xquik_search(None) is True
    assert should_use_xquik_search(AuthContext("token", "ct0")) is False

    monkeypatch.setenv("X_READ_BACKEND", "hermes")

    assert should_use_xquik_search(AuthContext("token", "ct0")) is True


def test_xquik_auth_headers():
    """Test Hermes Tweet API key header selection."""
    assert xquik_auth_headers("xq_test") == {"x-api-key": "xq_test"}
    assert xquik_auth_headers("other-token") == {
        "Authorization": "Bearer other-token"
    }


# ============================================================================
# Input Validation Tests (Pure Logic - No External Dependencies)
# ============================================================================


@pytest.mark.asyncio
async def test_get_tweets_invalid_count_non_numeric():
    """Test get_tweets rejects non-numeric count."""
    set_auth_context(AuthContext("token", "ct0"))

    with pytest.raises(RuntimeError, match="Invalid argument \\(count\\)"):
        await get_tweets("testuser", count="invalid")


@pytest.mark.asyncio
async def test_get_tweets_count_too_high():
    """Test get_tweets rejects count > 50."""
    set_auth_context(AuthContext("token", "ct0"))

    with pytest.raises(RuntimeError, match="max value is 50"):
        await get_tweets("testuser", count="100")


@pytest.mark.asyncio
async def test_get_tweets_count_zero():
    """Test get_tweets rejects count <= 0."""
    set_auth_context(AuthContext("token", "ct0"))

    with pytest.raises(RuntimeError, match="count cant be less then 0"):
        await get_tweets("testuser", count="0")


@pytest.mark.asyncio
async def test_search_tweets_invalid_count():
    """Test search_tweets validates count parameter."""
    set_auth_context(AuthContext("token", "ct0"))

    with pytest.raises(RuntimeError, match="max value is 50"):
        await search_tweets("python", count="51")


@pytest.mark.asyncio
@patch("main.httpx.AsyncClient")
async def test_search_tweets_with_xquik_backend(mock_client_class, monkeypatch):
    """Test search_tweets can use Hermes Tweet without cookie auth."""
    set_auth_context(None)
    monkeypatch.setenv("XQUIK_API_KEY", "xq_test")
    monkeypatch.setenv("XQUIK_BASE_URL", "https://example.test/")

    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "data": [
            {
                "id": "tweet123",
                "author": {"username": "alice"},
                "text": "Hermes search result",
                "createdAt": "2026-06-06T00:00:00Z",
                "public_metrics": {
                    "like_count": 12,
                    "reply_count": 3,
                    "retweet_count": 4,
                    "views": 100,
                },
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client
    mock_context.__aexit__.return_value = None
    mock_client_class.return_value = mock_context

    result = await search_tweets("AI agents", count="2")
    result_data = json.loads(result)

    assert result_data == [
        {
            "id": "tweet123",
            "in_reply_to": None,
            "author_username": "alice",
            "text": "Hermes search result",
            "lang": None,
            "created_at": "2026-06-06T00:00:00Z",
            "view_count": 100,
            "favorite_count": 12,
            "reply_count": 3,
            "retweet_count": 4,
        }
    ]
    mock_client.get.assert_awaited_once_with(
        "https://example.test/api/v1/x/tweets/search",
        params={"q": "AI agents", "queryType": "Top", "limit": 2},
        headers={"x-api-key": "xq_test"},
    )


@pytest.mark.asyncio
async def test_search_tweets_with_xquik_backend_requires_key(monkeypatch):
    """Test forced Hermes Tweet backend reports both key names."""
    set_auth_context(None)
    monkeypatch.delenv("HERMES_TWEET_API_KEY", raising=False)
    monkeypatch.delenv("XQUIK_API_KEY", raising=False)
    monkeypatch.setenv("X_READ_BACKEND", "hermes")

    with pytest.raises(RuntimeError, match="HERMES_TWEET_API_KEY or XQUIK_API_KEY"):
        await search_tweets("AI agents", count="2")


# ============================================================================
# Auth Requirement Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_tweets_requires_auth():
    """Test get_tweets raises error when not authenticated."""
    set_auth_context(None)

    with pytest.raises(RuntimeError, match="Authentication required"):
        await get_tweets("testuser")


@pytest.mark.asyncio
async def test_post_tweet_requires_auth():
    """Test post_tweet raises error when not authenticated."""
    set_auth_context(None)

    with pytest.raises(RuntimeError, match="Authentication required"):
        await post_tweet("Hello world")


@pytest.mark.asyncio
async def test_like_tweet_requires_auth():
    """Test like_tweet raises error when not authenticated."""
    set_auth_context(None)

    with pytest.raises(RuntimeError, match="Authentication required"):
        await like_tweet("123456")


# ============================================================================
# Mocked API Tests (Test Business Logic)
# ============================================================================


@pytest.mark.asyncio
@patch("main.Client")
async def test_get_tweets_success(mock_client_class):
    """Test get_tweets returns formatted tweet data."""
    set_auth_context(AuthContext("token", "ct0"))

    # Mock the Twitter API response
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client

    mock_user = Mock()
    mock_user.id = "user123"

    mock_tweet = Mock()
    mock_tweet.id = "tweet123"
    mock_tweet.in_reply_to = None
    mock_tweet.user.screen_name = "testuser"
    mock_tweet.text = "Test tweet content"
    mock_tweet.lang = "en"
    mock_tweet.created_at = "2024-01-01"
    mock_tweet.view_count = 100
    mock_tweet.favorite_count = 10
    mock_tweet.reply_count = 5
    mock_tweet.retweet_count = 2

    mock_client.get_user_by_screen_name.return_value = mock_user
    mock_client.get_user_tweets.return_value = [mock_tweet]

    result = await get_tweets("testuser", count="30")
    result_data = json.loads(result)

    assert len(result_data) == 1
    assert result_data[0]["id"] == "tweet123"
    assert result_data[0]["text"] == "Test tweet content"
    assert result_data[0]["author_username"] == "testuser"
    assert result_data[0]["favorite_count"] == 10


@pytest.mark.asyncio
@patch("main.Client")
async def test_get_profile_success(mock_client_class):
    """Test get_profile returns formatted user data."""
    set_auth_context(AuthContext("token", "ct0"))

    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client

    mock_user = Mock()
    mock_user.id = "123"
    mock_user.name = "Test User"
    mock_user.screen_name = "testuser"
    mock_user.created_at = "2020-01-01"
    mock_user.profile_image_url = "https://example.com/img.jpg"
    mock_user.url = "https://example.com"
    mock_user.location = "Earth"
    mock_user.description = "Test bio"
    mock_user.description_urls = []
    mock_user.is_blue_verified = False
    mock_user.verified = False
    mock_user.possibly_sensitive = False
    mock_user.can_dm = True
    mock_user.followers_count = 100
    mock_user.fast_followers_count = 10
    mock_user.normal_followers_count = 90
    mock_user.following_count = 50

    mock_client.get_user_by_screen_name.return_value = mock_user

    result = await get_profile("testuser")
    result_data = json.loads(result)

    assert result_data["username"] == "testuser"
    assert result_data["name"] == "Test User"
    assert result_data["followers_count"] == 100


@pytest.mark.asyncio
@patch("main.Client")
async def test_post_tweet_success(mock_client_class):
    """Test post_tweet calls API correctly."""
    set_auth_context(AuthContext("token", "ct0"))

    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    mock_client.create_tweet.return_value = None

    result = await post_tweet("Hello world")
    result_data = json.loads(result)

    assert result_data["status"] == "success"
    mock_client.create_tweet.assert_called_once_with(text="Hello world", reply_to=None)


@pytest.mark.asyncio
@patch("main.Client")
async def test_like_tweet_success(mock_client_class):
    """Test like_tweet calls favorite API."""
    set_auth_context(AuthContext("token", "ct0"))

    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client

    result = await like_tweet("123456", action="like")
    result_data = json.loads(result)

    assert result_data["status"] == "success"
    mock_client.favorite_tweet.assert_called_once_with("123456")


@pytest.mark.asyncio
@patch("main.Client")
async def test_unlike_tweet_success(mock_client_class):
    """Test unlike action calls unfavorite API."""
    set_auth_context(AuthContext("token", "ct0"))

    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client

    await like_tweet("123456", action="unlike")

    mock_client.unfavorite_tweet.assert_called_once_with("123456")


# ============================================================================
# Middleware Tests
# ============================================================================


@pytest.mark.asyncio
async def test_auth_middleware_valid_token():
    """Test middleware accepts valid Bearer token."""
    middleware = AuthMiddleware(app=Mock())

    request = Mock(spec=Request)
    request.method = "POST"
    request.url.path = "/mcp"
    request.headers.get.return_value = "Bearer auth_token_here:csrf_token_here"

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    call_next.assert_called_once()


@pytest.mark.asyncio
async def test_auth_middleware_invalid_format():
    """Test middleware rejects malformed Authorization header."""
    middleware = AuthMiddleware(app=Mock())

    request = Mock(spec=Request)
    request.method = "POST"
    request.url.path = "/mcp"
    request.headers.get.return_value = "InvalidFormat token"

    call_next = AsyncMock()

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 401
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_auth_middleware_health_check_bypass():
    """Test middleware allows health checks without auth."""
    middleware = AuthMiddleware(app=Mock())

    request = Mock(spec=Request)
    request.method = "GET"
    request.url.path = "/health"
    request.headers.get.return_value = None

    call_next = AsyncMock(return_value=JSONResponse({"status": "ok"}))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    call_next.assert_called_once()


def test_auth_middleware_validate_tokens():
    """Test token validation logic."""
    middleware = AuthMiddleware(app=Mock())

    assert middleware.validate_auth_token("valid_token") is True
    assert middleware.validate_auth_token("") is False

    assert middleware.validate_csrf_token("valid_csrf") is True
    assert middleware.validate_csrf_token("") is False
