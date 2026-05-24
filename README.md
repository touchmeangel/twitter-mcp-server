## twitter-mcp-server

Twitter client MCP Server where you only have to connect your account or auth token and let everything else be handled for you 

## Tools
### Reading Tools
- `get_tweets` - Retrieve the latest tweets from a specific user
- `get_profile` - Access profile details of a user
- `search_tweets` - Find tweets based on hashtags or keywords

### Interaction Tools
- `like_tweet` - Like or unlike a tweet
- `retweet` - Retweet or undo retweet
- `post_tweet` - Publish a new tweet, with optional media attachments

### Timeline Tools
- `get_timeline` - Fetch tweets from various timeline types
- `get_trends` - Retrieve currently trending topics

### User Management Tools
- `follow_user` - Follow or unfollow another user

## Usage
Add the server config to your MCP client:

On MacOS:
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

On Windows:
```bash
%APPDATA%/Claude/claude_desktop_config.json
```
Configuration:
```json
{
  "mcpServers": {
    "twitter-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--name", "twitter-mcp-server",
        "touchmeangel/twitter-mcp-server"
      ]
    }
  }
}
```
<b>Or run http server like this</b>
```bash
docker run -i --rm --name twitter-mcp-server -e APP_PORT=3000 -p 3000:3000 touchmeangel/twitter-mcp-server
```
<b>You can even just run it inside docker compose</b>
```docker-compose
services:
  twitter-mcp:
    image: touchmeangel/twitter-mcp-server
    restart: unless-stopped
    environment:
      - APP_PORT=3000
    ports:
      - 3000:3000
```
Now use `http://twitter-mcp:3000/mcp` or `http://localhost:3000/mcp` for connection
## Authentication
```
Authorization: Bearer <auth_token>:<ct0>
```
`auth_token` and `ct0` are X (Twitter) cookies which allow access to your account.

### Optional Hermes Tweet Backend

Read tools can use [Hermes Tweet](https://github.com/Xquik-dev/hermes-tweet) through Xquik instead of bearer cookie auth when an API key is configured:

```bash
XQUIK_API_KEY=xq_...
# Optional. Defaults to https://xquik.com.
XQUIK_BASE_URL=https://xquik.com
```

`get_tweets`, `get_profile`, `search_tweets`, and `get_replies` use the Hermes Tweet backend automatically when `XQUIK_API_KEY` or `HERMES_TWEET_API_KEY` is present. If the backend is unavailable and a bearer cookie header is present, the server falls back to the existing Twikit path.

Posting through Hermes Tweet is disabled by default. Enable it only for explicit write workflows:

```bash
XQUIK_ACCOUNT=@your_connected_account
HERMES_TWEET_ENABLE_ACTIONS=true
```

Without these write settings, `post_tweet` keeps using the existing cookie-authenticated Twikit path.

## Error Handling

The server implements comprehensive error handling:
- Input validation for all parameters
- Rate limiting protection
- Detailed error messages
- Proper error propagation
- Logging for debugging

## Development & Testing
Contributions are welcome! Please feel free to submit a Pull Request.

To test tools use
```bash
npx @modelcontextprotocol/inspector
```
