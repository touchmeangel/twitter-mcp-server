import asyncio
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from typing import Optional, Literal
from contextvars import ContextVar
from dataclasses import dataclass
from twikit import Client, errors
import logging
import uvicorn
from config import HOST, PORT
import json

logger = logging.getLogger(__name__)

mcp = FastMCP(
  name="twitter-mcp-server",
  host=HOST,
  port=int(PORT or "8080"),
  streamable_http_path="/mcp"
)
mcp.streamable_http_app()

@mcp.tool(description="Get recent tweets from a user")
async def get_tweets(
  username: str,
  count: str = "30"
) -> str:
  """
  Args:
    username: Username of the user (without @)
    count: Number of tweets to retrieve (default: 30, max: 50)
  """
  try:
    count_int = int(count)
  except ValueError:
    raise RuntimeError(f"Invalid argument (count)")
  if count_int > 50:
    raise RuntimeError(f"Invalid argument (count): max value is 50")
  if count_int <= 0:
    raise RuntimeError(f"Invalid argument (count): count cant be less then 0")
  
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})
  try:
    user = await client.get_user_by_screen_name(username)
    tweets = await client.get_user_tweets(user.id, "Tweets", count=count_int)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  result = []
  for tweet in tweets:
    result.append({"id": tweet.id, "in_reply_to": tweet.in_reply_to, "author_username": tweet.user.screen_name, "text": tweet.text, "lang": tweet.lang, "created_at": tweet.created_at, "view_count": tweet.view_count, "favorite_count": tweet.favorite_count, "reply_count": tweet.reply_count, "retweet_count": tweet.retweet_count})
  return json.dumps(result)

@mcp.tool(description="Get a Twitter user's profile information")
async def get_profile(
  username: str
) -> str:
  """
  Args:
    username: Username of the user (without @)
  """
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})

  try:
    user = await client.get_user_by_screen_name(username)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")
  
  return json.dumps({
    "id": user.id,
    "name": user.name,
    "username": user.screen_name,
    "created_at": user.created_at,
    "profile_image_url": user.profile_image_url,
    "url": user.url,
    "location": user.location,
    "description": user.description,
    "description_urls": user.description_urls,
    "is_blue_verified": user.is_blue_verified,
    "verified": user.verified,
    "possibly_sensitive": user.possibly_sensitive,
    "can_dm": user.can_dm,
    "followers_count": user.followers_count,
    "fast_followers_count": user.fast_followers_count,
    "normal_followers_count": user.normal_followers_count,
    "following_count": user.following_count
  })

@mcp.tool(description="Search for tweets by hashtag or keyword")
async def search_tweets(
  query: str,
  mode: Literal["Latest", "Top"] = "Top",
  count: str = "30"
) -> str:
  """
  Args:
    query: Search query (hashtag or keyword). For hashtags, include the # symbol
    mode: Search mode - 'latest' for most recent tweets or 'top' for most relevant tweets (default: 'top')
    count: Number of tweets to retrieve (default: 30, max: 50)
  """
  try:
    count_int = int(count)
  except ValueError:
    raise RuntimeError(f"Invalid argument (count)")
  if count_int > 50:
    raise RuntimeError(f"Invalid argument (count): max value is 50")
  if count_int <= 0:
    raise RuntimeError(f"Invalid argument (count): count cant be less then 0")

  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})
  try:
    tweets = await client.search_tweet(query, mode, count=count_int)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  result = []
  for tweet in tweets:
    result.append({"id": tweet.id, "in_reply_to": tweet.in_reply_to, "author_username": tweet.user.screen_name, "text": tweet.text, "lang": tweet.lang, "created_at": tweet.created_at, "view_count": tweet.view_count, "favorite_count": tweet.favorite_count, "reply_count": tweet.reply_count, "retweet_count": tweet.retweet_count})
  return json.dumps(result)

@mcp.tool(description="Like or unlike a tweet")
async def like_tweet(
  tweet_id: str,
  action: Literal["like", "unlike"] = "like"
) -> str:
  """
  Args:
    tweet_id: ID of the tweet to like/unlike
    action: Whether to \"like\" or \"unlike\" the tweet
  """
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})

  try:
    if action == "like":
      await client.favorite_tweet(tweet_id)
    elif action == "unlike":
      await client.unfavorite_tweet(tweet_id)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  return json.dumps({"status": "success"})

@mcp.tool(description="Retweet or undo retweet of a tweet")
async def retweet(
  tweet_id: str,
  action: Literal["retweet", "undo"] = "retweet"
) -> str:
  """
  Args:
    tweet_id: ID of the tweet to retweet/undo retweet
    action: Whether to \"retweet\" or \"undo\" the retweet
  """
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})

  try:
    if action == "retweet":
      await client.retweet(tweet_id)
    elif action == "undo":
      await client.delete_retweet(tweet_id)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  return json.dumps({"status": "success"})

@mcp.tool(description="Post a new tweet, optionally with media or as a quote tweet")
async def post_tweet(
  text: str,
  reply_to_tweet_id: str = "",
) -> str:
  """
  Args:
    text: The text content of the tweet limited to 280 characters
    reply_to_tweet_id: Optional ID of the tweet to reply to
  """
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})
  try:
    await client.create_tweet(text=text, reply_to=None if reply_to_tweet_id == "" else reply_to_tweet_id)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")
  
  return json.dumps({"status": "success"})

@mcp.tool(description="Get current trending topics on Twitter")
async def get_trends(
  category: Literal['trending', 'for-you', 'news', 'sports', 'entertainment'] = 'trending',
  count: str = "30"
) -> str:
  """
  Args:
    category: Search mode - 'trending' for overall trends, 'for-you', 'news', 'sports', 'entertainment' for more specific trends
    count: Number of trends to retrieve (default: 30, max: 50)
  """
  try:
    count_int = int(count)
  except ValueError:
    raise RuntimeError(f"Invalid argument (count)")
  if count_int > 50:
    raise RuntimeError(f"Invalid argument (count): max value is 50")
  if count_int <= 0:
    raise RuntimeError(f"Invalid argument (count): count cant be less then 0")
  
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})

  try:
    trends = await client.get_trends(category, count=count_int, retry=False)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")
  
  result = []
  for trend in trends:
    result.append({"name": trend.name, "tweet_count": trend.tweets_count, "grouped_trends": trend.grouped_trends, "domain_context": trend.domain_context})
  return json.dumps(result)

@mcp.tool(description="Get tweets from a user's home personalized timeline")
async def get_timeline(
  category: Literal['for-you', 'following'] = 'for-you',
  count: str = "40"
) -> str:
  """
  Args:
    category: mode - 'for-you' for personalized home for-you feed, 'following' for your following timeline
    count: Number of tweets to retrieve (default: 40, max: 50)
  """
  try:
    count_int = int(count)
  except ValueError:
    raise RuntimeError(f"Invalid argument (count)")  
  if count_int > 50:
    raise RuntimeError(f"Invalid argument (count): max value is 50")
  if count_int <= 0:
    raise RuntimeError(f"Invalid argument (count): count cant be less then 0")
  
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})
  try:
    if category == "for-you":
      tweets = await client.get_timeline(count=count_int)
    elif category == "following":
      tweets = await client.get_latest_timeline(count=count_int)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")
  
  result = []
  for tweet in tweets:
    result.append({"id": tweet.id, "in_reply_to": tweet.in_reply_to, "author_username": tweet.user.screen_name, "text": tweet.text, "lang": tweet.lang, "created_at": tweet.created_at, "view_count": tweet.view_count, "favorite_count": tweet.favorite_count, "reply_count": tweet.reply_count, "retweet_count": tweet.retweet_count})
  return json.dumps(result)

@mcp.tool(description="Follow or unfollow a Twitter user")
async def follow_user(
  username: str,
  action: Literal["follow", "unfollow"] = "follow"
) -> str:
  """
  Args:
    username: Username of the user to follow/unfollow (without @)
    action: Whether to follow or unfollow the user
  """  
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})
  try:
    user = await client.get_user_by_screen_name(username)
    if action == "follow":
      await client.follow_user(user.id)
    elif action == "unfollow":
      await client.unfollow_user(user.id)
  except errors.Forbidden:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  return json.dumps({"status": "success"})

@mcp.tool(description="Read replies under post")
async def get_replies(
  tweet_id: str,
  count: str = "30"
) -> str:
  """
  Args:
      tweet_id: ID of the tweet to get replies of
      count: Number of replies to retrieve (default: 30, max: 50)
  """
  try:
    count_int = int(count)
  except ValueError:
    raise RuntimeError(f"Invalid argument (count)")  
  if count_int > 50:
    raise RuntimeError(f"Invalid argument (count): max value is 50")
  if count_int <= 0:
    raise RuntimeError(f"Invalid argument (count): count cant be less then 0")
  
  auth = get_auth_context()
  if auth is None:
    raise RuntimeError(f"Authentication required: AUTH_REQUIRED")

  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "ct0": auth.ct0})

  replies = await client._get_more_replies(tweet_id, None)
  result = []
  for reply in replies:
    result.append({"id": reply.id, "in_reply_to": reply.in_reply_to, "author_username": reply.user.screen_name, "text": reply.text, "lang": reply.lang, "created_at": reply.created_at, "view_count": reply.view_count, "favorite_count": reply.favorite_count, "reply_count": reply.reply_count, "retweet_count": reply.retweet_count})
  return json.dumps(result)

_auth_context: ContextVar[Optional['AuthContext']] = ContextVar('auth_context', default=None)

@dataclass
class AuthContext:
  auth_token: str
  ct0: str

def set_auth_context(auth: Optional[AuthContext]) -> None:
  """Set the authentication context for the current async context."""
  _auth_context.set(auth)

def get_auth_context() -> Optional[AuthContext]:
  """Get the authentication context from the current async context."""
  return _auth_context.get()

class AuthMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next):
    if request.method == "OPTIONS":
      return await call_next(request)
  
    if request.url.path in ["/health", "/docs", "/.well-known/health"]:
      return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
      return await call_next(request)
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
      return JSONResponse(
        status_code=401,
        content={"error": "Invalid Authorization header format"}
      )
    
    token = parts[1]
    token_parts = token.split(sep=":")
    auth_token = token_parts[0]
    csrf_token = token_parts[1]
    
    if not self.validate_auth_token(auth_token) or not self.validate_csrf_token(csrf_token):
      return JSONResponse(
        status_code=401,
        content={"error": "Invalid or expired token"}
      )
    
    set_auth_context(AuthContext(auth_token, csrf_token))    
    response = await call_next(request)
    return response
  
  def validate_auth_token(self, token: str) -> bool:
    return len(token) > 0
  
  def validate_csrf_token(self, token: str) -> bool:
    return len(token) > 0

async def main():
  if PORT:
    mcp_app = mcp.streamable_http_app()
    mcp_app.add_middleware(AuthMiddleware)
    mcp_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Session-ID", "mcp-session-id"])
    config = uvicorn.Config(
      mcp_app,
      host=mcp.settings.host,
      port=mcp.settings.port,
      log_level=mcp.settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()
  else:
    await mcp.run_stdio_async()

if __name__ == "__main__":
  asyncio.run(main())