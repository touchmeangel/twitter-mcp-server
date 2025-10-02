import asyncio
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional, Literal
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.requests import Request
from contextvars import ContextVar
from dataclasses import dataclass
from twikit import Client
import logging
import uvicorn
from config import HOST, PORT

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
  count: Optional[int] = 10
) -> str:
  """
  Args:
    username: Username of the user (without @)
    count: Number of tweets to retrieve (default: 10, max: 50)
  """
  # Implementation here
  pass

@mcp.tool(description="Get a Twitter user's profile information")
async def get_profile(
  username: str
) -> str:
  """
  Args:
    username: Username of the user (without @)
  """
  # Implementation here
  pass

@mcp.tool(description="Search for tweets by hashtag or keyword")
async def search_tweets(
  query: str,
  mode: Literal["Latest", "Top"] = "Latest",
  count: Optional[int] = 10
) -> str:
  """
  Args:
    query: Search query (hashtag or keyword). For hashtags, include the # symbol
    mode: Search mode - 'latest' for most recent tweets or 'top' for most relevant tweets
    count: Number of tweets to retrieve (default: 10, max: 50)
  """
  auth = get_auth_context()
  if auth is None:
    logging.warning("no auth")
    return
  client = Client('en-US')
  client.set_cookies({"auth_token": auth.auth_token, "cf0": auth.cf0})
  tweets = await client.search_tweet(query, mode, count=count)

  logger.warning(f"t: {tweets}")

@mcp.tool(description="Like or unlike a tweet")
async def like_tweet(
  tweet_id: str,
  action: Literal["like", "unlike"] = "like"
) -> str:
  """
  Args:
    tweet_id: ID of the tweet to like/unlike
    action: Whether to like or unlike the tweet
  """
  # Implementation here
  pass


@mcp.tool(description="Retweet or undo retweet of a tweet")
async def retweet(
  tweet_id: str,
  action: Literal["retweet", "undo"] = "retweet"
) -> str:
  """
  Args:
    tweet_id: ID of the tweet to retweet/undo retweet
    action: Whether to retweet or undo the retweet
  """
  # Implementation here
  pass


@mcp.tool(description="Post a new tweet, optionally with media or as a quote tweet")
async def post_tweet(
  text: str,
  reply_to_tweet_id: Optional[str] = None,
  quote_tweet_id: Optional[str] = None,
  media: Optional[List[dict]] = None,
  hide_link_preview: bool = False
) -> str:
  """
  Args:
    text: The text content of the tweet
    reply_to_tweet_id: Optional ID of the tweet to reply to
    quote_tweet_id: Optional ID of the tweet to quote
    media: Optional array of media items with 'data' (base64) and 'media_type' (MIME type)
    hide_link_preview: Whether to hide link previews in the tweet
  """
  # Implementation here
  pass


@mcp.tool(description="Get current trending topics on Twitter")
async def get_trends() -> str:
  """Get current trending topics on Twitter"""
  # Implementation here
  pass


@mcp.tool(description="Get a user's followers or following list")
async def get_user_relationships(
  username: str,
  relationship_type: Literal["followers", "following"],
  count: Optional[int] = 10
) -> str:
  """
  Args:
    username: Username of the user (without @)
    relationship_type: Whether to get followers or following list
    count: Number of profiles to retrieve (default: 10, max: 50)
  """
  # Implementation here
  pass


@mcp.tool(description="Get tweets from a user's timeline or home timeline")
async def get_timeline(
  timeline_type: Literal["home", "following", "user"],
  username: Optional[str] = None,
  count: Optional[int] = 10
) -> str:
  """
  Args:
    timeline_type: Type of timeline - 'home' for personalized, 'following' for people you follow, or 'user' for specific user
    username: Username of the user whose timeline to fetch (required only for timeline_type='user')
    count: Number of tweets to retrieve (default: 10, max: 50)
  """
  # Implementation here
  pass


@mcp.tool(description="Get tweets from a Twitter list")
async def get_list_tweets(
  list_id: str,
  count: Optional[int] = 10
) -> str:
  """
  Args:
    list_id: ID of the Twitter list to fetch tweets from
    count: Number of tweets to retrieve (default: 10, max: 50)
  """
  # Implementation here
  pass


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
  # Implementation here
  pass

@mcp.tool(description="Create a Twitter thread (a series of connected tweets)")
async def create_thread(
    tweets: List[dict]
) -> str:
    """
    Args:
      tweets: Array of tweet objects with 'text' (required) and optional 'media' array
              Each media item should have 'data' (base64) and 'media_type' (MIME type)
    """
    # Implementation here
    pass

_auth_context: ContextVar[Optional['AuthContext']] = ContextVar('auth_context', default=None)

@dataclass
class AuthContext:
  auth_token: str
  cf0: str

def set_auth_context(auth: Optional[AuthContext]) -> None:
  """Set the authentication context for the current async context."""
  _auth_context.set(auth)

def get_auth_context() -> Optional[AuthContext]:
  """Get the authentication context from the current async context."""
  return _auth_context.get()

class AuthMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next):
    if request.url.path in ["/health", "/docs"]:
      return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
      return JSONResponse(
        status_code=401,
        content={"error": "Missing Authorization header"}
      )
    
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
    
    client = Client("en-US")
    client.set_cookies({"auth_token": auth_token, "cf0": csrf_token})
    await client.user()

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
    mcp_app.add_middleware(Middleware(AuthMiddleware))
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