import json
import unittest

from urllib.error import HTTPError

from xquik_client import XquikClient, XquikError


class FakeResponse:
  def __init__(self, payload):
    self.payload = payload

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    return False

  def read(self):
    return json.dumps(self.payload).encode("utf-8")

  def close(self):
    return None


class FakeOpener:
  def __init__(self, payload):
    self.payload = payload
    self.requests = []

  def __call__(self, request, timeout):
    self.requests.append((request, timeout))
    return FakeResponse(self.payload)


class XquikClientTest(unittest.TestCase):
  def test_search_tweets_builds_query_and_normalizes_results(self):
    opener = FakeOpener(
      {
        "tweets": [
          {
            "tweetId": "1",
            "content": "hello",
            "user": {"screen_name": "alice"},
            "favoriteCount": 3,
            "retweetCount": 2,
          }
        ]
      }
    )
    client = XquikClient(api_key="xq_test", opener=opener)

    result = client.search_tweets("ai agents", "Latest", 5)

    request, timeout = opener.requests[0]
    self.assertEqual(timeout, 30)
    self.assertIn("/api/v1/x/tweets/search?", request.full_url)
    self.assertIn("q=ai+agents", request.full_url)
    self.assertIn("queryType=Latest", request.full_url)
    self.assertEqual(request.get_header("X-api-key"), "xq_test")
    self.assertEqual(result[0]["id"], "1")
    self.assertEqual(result[0]["author_username"], "alice")
    self.assertEqual(result[0]["favorite_count"], 3)

  def test_get_profile_accepts_bearer_tokens(self):
    opener = FakeOpener(
      {
        "data": {
          "id": "42",
          "screen_name": "alice",
          "public_metrics": {"followers_count": 9, "following_count": 4},
        }
      }
    )
    client = XquikClient(api_key="plain-token", opener=opener)

    result = client.get_profile("@alice")

    request, _ = opener.requests[0]
    self.assertTrue(request.full_url.endswith("/api/v1/x/users/alice"))
    self.assertEqual(request.get_header("Authorization"), "Bearer plain-token")
    self.assertEqual(result["username"], "alice")
    self.assertEqual(result["followers_count"], 9)

  def test_get_tweets_reads_nested_data(self):
    opener = FakeOpener(
      {
        "data": {
          "tweets": [
            {
              "id": "10",
              "text": "nested",
              "author": {"username": "bob"},
              "replyCount": 1,
            }
          ]
        }
      }
    )
    client = XquikClient(api_key="xq_test", opener=opener)

    result = client.get_tweets("bob", 2)

    request, _ = opener.requests[0]
    self.assertIn("/api/v1/x/users/bob/tweets?limit=2", request.full_url)
    self.assertEqual(result[0]["id"], "10")
    self.assertEqual(result[0]["author_username"], "bob")
    self.assertEqual(result[0]["reply_count"], 1)

  def test_post_tweet_requires_action_configuration(self):
    client = XquikClient(api_key="xq_test")

    with self.assertRaises(XquikError):
      client.post_tweet("hello")

  def test_post_tweet_sends_account_and_reply(self):
    opener = FakeOpener({"tweet": {"id": "99"}})
    client = XquikClient(
      api_key="xq_test",
      account="@alice",
      actions_enabled=True,
      opener=opener,
    )

    result = client.post_tweet("hello", "88")

    request, _ = opener.requests[0]
    self.assertEqual(request.full_url, "https://xquik.com/api/v1/x/tweets")
    self.assertEqual(request.get_method(), "POST")
    self.assertEqual(json.loads(request.data.decode("utf-8")), {
      "account": "@alice",
      "text": "hello",
      "replyToTweetId": "88",
    })
    self.assertEqual(result["tweet_id"], "99")

  def test_http_errors_raise_backend_error(self):
    class ErrorOpener:
      def __call__(self, request, timeout):
        raise HTTPError(request.full_url, 402, "Payment Required", {}, FakeResponse({"error": "insufficient_credits"}))

    client = XquikClient(api_key="xq_test", opener=ErrorOpener())

    with self.assertRaisesRegex(XquikError, "insufficient_credits"):
      client.search_tweets("ai", "Top", 1)


if __name__ == "__main__":
  unittest.main()
