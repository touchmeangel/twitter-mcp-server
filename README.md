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
- `create_thread` - Post a Twitter thread

### Timeline Tools
- `get_timeline` - Fetch tweets from various timeline types
- `get_trends` - Retrieve currently trending topics

### User Management Tools
- `get_user_relationships` - View a user's followers or accounts they follow
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

## Authentication

## Development & Testing
Contributions are welcome! Please feel free to submit a Pull Request.

To test tools use
```bash
npx @modelcontextprotocol/inspector
```

## Error Handling

The server implements comprehensive error handling:
- Input validation for all parameters
- Rate limiting protection
- Detailed error messages
- Proper error propagation
- Logging for debugging