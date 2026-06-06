from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import aiohttp

DEFAULT_BASE_URL = "https://xquik.com"
DEFAULT_TIMEOUT = 30


class XquikError(RuntimeError):
    """Raised when the optional Xquik backend cannot complete a request."""


class XquikClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        account: str = "",
        actions_enabled: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("XQUIK_BASE_URL must use http or https")
        self.account = account.strip()
        self.actions_enabled = actions_enabled
        self.timeout = timeout
        self.session = session

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> XquikClient:
        source = env if env is not None else os.environ
        api_key = source.get("XQUIK_API_KEY") or ""
        base_url = source.get("XQUIK_BASE_URL") or DEFAULT_BASE_URL
        account = source.get("XQUIK_ACCOUNT") or ""
        actions_enabled = source.get("XQUIK_ENABLE_ACTIONS", "").lower() in {
            "1",
            "true",
            "yes",
        }
        return cls(
            api_key=api_key,
            base_url=base_url,
            account=account,
            actions_enabled=actions_enabled,
        )

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def can_create_tweets(self) -> bool:
        return self.is_configured() and self.actions_enabled and bool(self.account)

    async def get_tweets(self, username: str, count: int) -> list[dict[str, Any]]:
        payload = await self._request_json(
            "GET",
            f"/api/v1/x/users/{quote(username.lstrip('@'))}/tweets",
            query={"limit": count},
        )
        return [
            self._normalize_tweet(tweet)
            for tweet in self._extract_items(payload, "tweets")
        ]

    async def get_profile(self, username: str) -> dict[str, Any]:
        payload = await self._request_json(
            "GET", f"/api/v1/x/users/{quote(username.lstrip('@'))}"
        )
        profile = self._extract_object(payload, "profile", "user")
        return self._normalize_profile(profile)

    async def search_tweets(
        self, query: str, mode: str, count: int
    ) -> list[dict[str, Any]]:
        payload = await self._request_json(
            "GET",
            "/api/v1/x/tweets/search",
            query={"q": query, "queryType": mode, "limit": count},
        )
        return [
            self._normalize_tweet(tweet)
            for tweet in self._extract_items(payload, "tweets")
        ]

    async def get_replies(self, tweet_id: str) -> list[dict[str, Any]]:
        payload = await self._request_json(
            "GET", f"/api/v1/x/tweets/{quote(tweet_id)}/replies"
        )
        return [
            self._normalize_tweet(tweet)
            for tweet in self._extract_items(payload, "replies", "tweets")
        ]

    async def post_tweet(
        self, text: str, reply_to_tweet_id: str = ""
    ) -> dict[str, Any]:
        if not self.can_create_tweets():
            raise XquikError(
                "Xquik posting requires XQUIK_API_KEY, XQUIK_ACCOUNT, and XQUIK_ENABLE_ACTIONS=true."
            )

        body: dict[str, Any] = {"account": self.account, "text": text}
        if reply_to_tweet_id:
            body["replyToTweetId"] = reply_to_tweet_id

        payload = await self._request_json("POST", "/api/v1/x/tweets", body=body)
        tweet = self._extract_object(payload, "tweet", "data")
        tweet_id = (
            tweet.get("id") or tweet.get("tweetId") or payload.get("id")
            if isinstance(payload, dict)
            else None
        )
        if not tweet_id:
            raise XquikError("Xquik post_tweet response missing tweet id.")
        return {"status": "success", "tweet_id": tweet_id, "data": payload}

    async def _request_json(
        self,
        method: str,
        path: str,
        query: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        if not self.api_key:
            raise XquikError("Xquik backend is not configured.")

        query_string = urlencode(
            {key: value for key, value in (query or {}).items() if value is not None}
        )
        url = f"{self.base_url}{path}"
        if query_string:
            url = f"{url}?{query_string}"

        headers = self._headers(has_body=body is not None)

        timeout = aiohttp.ClientTimeout(total=self.timeout)
        try:
            if self.session is not None:
                async with self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=body,
                    timeout=timeout,
                ) as response:
                    return await self._decode_response(response)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method, url, headers=headers, json=body
                ) as response:
                    return await self._decode_response(response)
        except TimeoutError as exc:
            raise XquikError("Xquik request timed out.") from exc
        except aiohttp.ClientError as exc:
            raise XquikError(f"Xquik request failed: {exc}") from exc

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key.startswith("xq_"):
            headers["x-api-key"] = self.api_key
        else:
            headers["authorization"] = f"Bearer {self.api_key}"
        if has_body:
            headers["content-type"] = "application/json"
        return headers

    async def _decode_response(self, response: aiohttp.ClientResponse) -> Any:
        raw = await response.read()
        if response.status >= 400:
            detail = self._error_detail(raw, response.reason)
            raise XquikError(
                f"Xquik request failed with HTTP {response.status}: {detail}"
            )
        return self._decode_json(raw)

    def _error_detail(self, raw: bytes, reason: str | None) -> str:
        try:
            payload = self._decode_json(raw)
        except (ValueError, OSError):
            return reason or "request failed"
        if isinstance(payload, dict):
            return str(payload.get("error") or payload.get("message") or payload)
        return str(payload)

    def _decode_json(self, raw: bytes) -> Any:
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _extract_items(self, payload: Any, *keys: str) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        for key in keys + ("items", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = self._extract_items(value, *keys)
                if nested:
                    return nested
        return []

    def _extract_object(self, payload: Any, *keys: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        for key in keys:
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        return payload

    def _first_present(self, obj: Mapping[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in obj and obj[key] is not None:
                return obj[key]
        return None

    def _normalize_tweet(self, tweet: Any) -> dict[str, Any]:
        if not isinstance(tweet, dict):
            return {}

        user = tweet.get("user") if isinstance(tweet.get("user"), dict) else {}
        author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
        return {
            "id": self._first_present(tweet, "id", "id_str", "tweetId", "tweet_id"),
            "in_reply_to": self._first_present(
                tweet, "in_reply_to", "inReplyToTweetId"
            ),
            "author_username": (
                self._first_present(tweet, "author_username", "username")
                or self._first_present(user, "screen_name", "username")
                or self._first_present(author, "username", "screen_name")
            ),
            "text": self._first_present(tweet, "text", "full_text", "content"),
            "lang": self._first_present(tweet, "lang"),
            "created_at": self._first_present(tweet, "created_at", "createdAt"),
            "view_count": self._first_present(tweet, "view_count", "viewCount"),
            "favorite_count": self._first_present(
                tweet, "favorite_count", "like_count", "favoriteCount"
            ),
            "reply_count": self._first_present(tweet, "reply_count", "replyCount"),
            "retweet_count": self._first_present(
                tweet, "retweet_count", "retweetCount"
            ),
        }

    def _normalize_profile(self, profile: Mapping[str, Any]) -> dict[str, Any]:
        metrics = (
            profile.get("public_metrics")
            if isinstance(profile.get("public_metrics"), dict)
            else {}
        )
        followers_count = self._first_present(
            profile, "followers_count", "followersCount"
        )
        if followers_count is None:
            followers_count = self._first_present(metrics, "followers_count")

        following_count = self._first_present(
            profile, "following_count", "followingCount"
        )
        if following_count is None:
            following_count = self._first_present(metrics, "following_count")

        return {
            "id": self._first_present(profile, "id", "userId", "user_id"),
            "name": self._first_present(profile, "name"),
            "username": self._first_present(profile, "username", "screen_name"),
            "created_at": self._first_present(profile, "created_at", "createdAt"),
            "profile_image_url": self._first_present(
                profile, "profile_image_url", "profileImageUrl"
            ),
            "url": self._first_present(profile, "url"),
            "location": self._first_present(profile, "location"),
            "description": self._first_present(profile, "description", "bio"),
            "description_urls": self._first_present(
                profile, "description_urls", "descriptionUrls"
            ),
            "is_blue_verified": self._first_present(
                profile, "is_blue_verified", "isBlueVerified"
            ),
            "verified": self._first_present(profile, "verified"),
            "possibly_sensitive": self._first_present(
                profile, "possibly_sensitive", "possiblySensitive"
            ),
            "can_dm": self._first_present(profile, "can_dm", "canDm"),
            "followers_count": followers_count,
            "fast_followers_count": self._first_present(
                profile, "fast_followers_count", "fastFollowersCount"
            ),
            "normal_followers_count": self._first_present(
                profile, "normal_followers_count", "normalFollowersCount"
            ),
            "following_count": following_count,
        }
