import asyncio
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict, List, Optional, Literal
import twitter
import config

mcp = FastMCP(
  name="twitter-mcp-server",
  host=config.HOST,
  port=int(config.PORT or "8080"),
)

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
  mode: Literal["latest", "top"] = "latest",
  count: Optional[int] = 10
) -> str:
  """
  Args:
    query: Search query (hashtag or keyword). For hashtags, include the # symbol
    mode: Search mode - 'latest' for most recent tweets or 'top' for most relevant tweets
    count: Number of tweets to retrieve (default: 10, max: 50)
  """
  

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

if __name__ == "__main__":
  if config.PORT:
    asyncio.run(mcp.run_streamable_http_async())
  else:
    asyncio.run(mcp.run_stdio_async())