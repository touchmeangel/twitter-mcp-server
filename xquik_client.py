from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


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
    opener: Any = urlopen,
  ) -> None:
    self.api_key = api_key.strip()
    self.base_url = base_url.rstrip("/")
    self.account = account.strip()
    self.actions_enabled = actions_enabled
    self.timeout = timeout
    self.opener = opener

  @classmethod
  def from_env(cls, env: Mapping[str, str] | None = None) -> "XquikClient":
    source = env if env is not None else os.environ
    api_key = source.get("XQUIK_API_KEY") or ""
    base_url = source.get("XQUIK_BASE_URL") or DEFAULT_BASE_URL
    account = source.get("XQUIK_ACCOUNT") or ""
    actions_enabled = source.get("XQUIK_ENABLE_ACTIONS", "").lower() in {"1", "true", "yes"}
    return cls(api_key=api_key, base_url=base_url, account=account, actions_enabled=actions_enabled)

  def is_configured(self) -> bool:
    return bool(self.api_key)

  def can_create_tweets(self) -> bool:
    return self.is_configured() and self.actions_enabled and bool(self.account)

  def get_tweets(self, username: str, count: int) -> list[dict[str, Any]]:
    payload = self._request_json(
      "GET",
      f"/api/v1/x/users/{quote(username.lstrip('@'))}/tweets",
      query={"limit": count},
    )
    return [self._normalize_tweet(tweet) for tweet in self._extract_items(payload, "tweets")]

  def get_profile(self, username: str) -> dict[str, Any]:
    payload = self._request_json("GET", f"/api/v1/x/users/{quote(username.lstrip('@'))}")
    profile = self._extract_object(payload, "profile", "user")
    return self._normalize_profile(profile)

  def search_tweets(self, query: str, mode: str, count: int) -> list[dict[str, Any]]:
    payload = self._request_json(
      "GET",
      "/api/v1/x/tweets/search",
      query={"q": query, "queryType": mode, "limit": count},
    )
    return [self._normalize_tweet(tweet) for tweet in self._extract_items(payload, "tweets")]

  def get_replies(self, tweet_id: str) -> list[dict[str, Any]]:
    payload = self._request_json("GET", f"/api/v1/x/tweets/{quote(tweet_id)}/replies")
    return [self._normalize_tweet(tweet) for tweet in self._extract_items(payload, "replies", "tweets")]

  def post_tweet(self, text: str, reply_to_tweet_id: str = "") -> dict[str, Any]:
    if not self.can_create_tweets():
      raise XquikError(
        "Xquik posting requires XQUIK_API_KEY, XQUIK_ACCOUNT, and XQUIK_ENABLE_ACTIONS=true."
      )

    body: dict[str, Any] = {"account": self.account, "text": text}
    if reply_to_tweet_id:
      body["replyToTweetId"] = reply_to_tweet_id

    payload = self._request_json("POST", "/api/v1/x/tweets", body=body)
    tweet = self._extract_object(payload, "tweet", "data")
    tweet_id = tweet.get("id") or tweet.get("tweetId") or payload.get("id") if isinstance(payload, dict) else None
    return {"status": "success", "tweet_id": tweet_id, "data": payload}

  def _request_json(
    self,
    method: str,
    path: str,
    query: Mapping[str, Any] | None = None,
    body: Mapping[str, Any] | None = None,
  ) -> Any:
    if not self.api_key:
      raise XquikError("Xquik backend is not configured.")

    query_string = urlencode({key: value for key, value in (query or {}).items() if value is not None})
    url = f"{self.base_url}{path}"
    if query_string:
      url = f"{url}?{query_string}"

    request_body = None
    headers = self._headers(has_body=body is not None)
    if body is not None:
      request_body = json.dumps(body).encode("utf-8")

    request = Request(url, data=request_body, headers=headers, method=method)
    try:
      with self.opener(request, timeout=self.timeout) as response:
        return self._decode_json(response.read())
    except HTTPError as exc:
      detail = self._error_detail(exc)
      raise XquikError(f"Xquik request failed with HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
      raise XquikError(f"Xquik request failed: {exc.reason}") from exc

  def _headers(self, has_body: bool) -> dict[str, str]:
    headers: dict[str, str] = {}
    if self.api_key.startswith("xq_"):
      headers["x-api-key"] = self.api_key
    else:
      headers["authorization"] = f"Bearer {self.api_key}"
    if has_body:
      headers["content-type"] = "application/json"
    return headers

  def _error_detail(self, exc: HTTPError) -> str:
    try:
      payload = self._decode_json(exc.read())
    except (ValueError, OSError):
      return exc.reason or "request failed"
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

  def _normalize_tweet(self, tweet: Any) -> dict[str, Any]:
    if not isinstance(tweet, dict):
      return {}

    user = tweet.get("user") if isinstance(tweet.get("user"), dict) else {}
    author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
    return {
      "id": tweet.get("id") or tweet.get("id_str") or tweet.get("tweetId") or tweet.get("tweet_id"),
      "in_reply_to": tweet.get("in_reply_to") or tweet.get("inReplyToTweetId"),
      "author_username": (
        tweet.get("author_username")
        or tweet.get("username")
        or user.get("screen_name")
        or user.get("username")
        or author.get("username")
        or author.get("screen_name")
      ),
      "text": tweet.get("text") or tweet.get("full_text") or tweet.get("content"),
      "lang": tweet.get("lang"),
      "created_at": tweet.get("created_at") or tweet.get("createdAt"),
      "view_count": tweet.get("view_count") or tweet.get("viewCount"),
      "favorite_count": tweet.get("favorite_count") or tweet.get("like_count") or tweet.get("favoriteCount"),
      "reply_count": tweet.get("reply_count") or tweet.get("replyCount"),
      "retweet_count": tweet.get("retweet_count") or tweet.get("retweetCount"),
    }

  def _normalize_profile(self, profile: Mapping[str, Any]) -> dict[str, Any]:
    metrics = profile.get("public_metrics") if isinstance(profile.get("public_metrics"), dict) else {}
    return {
      "id": profile.get("id") or profile.get("userId") or profile.get("user_id"),
      "name": profile.get("name"),
      "username": profile.get("username") or profile.get("screen_name"),
      "created_at": profile.get("created_at") or profile.get("createdAt"),
      "profile_image_url": profile.get("profile_image_url") or profile.get("profileImageUrl"),
      "url": profile.get("url"),
      "location": profile.get("location"),
      "description": profile.get("description") or profile.get("bio"),
      "description_urls": profile.get("description_urls") or profile.get("descriptionUrls"),
      "is_blue_verified": profile.get("is_blue_verified") or profile.get("isBlueVerified"),
      "verified": profile.get("verified"),
      "possibly_sensitive": profile.get("possibly_sensitive") or profile.get("possiblySensitive"),
      "can_dm": profile.get("can_dm") or profile.get("canDm"),
      "followers_count": profile.get("followers_count") or profile.get("followersCount") or metrics.get("followers_count"),
      "fast_followers_count": profile.get("fast_followers_count") or profile.get("fastFollowersCount"),
      "normal_followers_count": profile.get("normal_followers_count") or profile.get("normalFollowersCount"),
      "following_count": profile.get("following_count") or profile.get("followingCount") or metrics.get("following_count"),
    }
