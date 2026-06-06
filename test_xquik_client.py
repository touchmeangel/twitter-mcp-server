import json
import unittest

from xquik_client import XquikClient, XquikError


class FakeResponse:
    def __init__(self, payload, status=200, reason="OK"):
        self.payload = payload
        self.status = status
        self.reason = reason

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeSession:
    def __init__(self, payload, status=200, reason="OK"):
        self.response = FakeResponse(payload, status=status, reason=reason)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.response


class XquikClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_search_tweets_builds_query_and_normalizes_results(self):
        session = FakeSession(
            {
                "tweets": [
                    {
                        "tweetId": "1",
                        "content": "hello",
                        "user": {"screen_name": "alice"},
                        "viewCount": 0,
                        "favoriteCount": 3,
                        "retweetCount": 2,
                    }
                ]
            }
        )
        client = XquikClient(api_key="xq_test", session=session)

        result = await client.search_tweets("ai agents", "Latest", 5)

        method, url, kwargs = session.requests[0]
        self.assertEqual(method, "GET")
        self.assertIn("/api/v1/x/tweets/search?", url)
        self.assertIn("q=ai+agents", url)
        self.assertIn("queryType=Latest", url)
        self.assertEqual(kwargs["headers"]["x-api-key"], "xq_test")
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[0]["author_username"], "alice")
        self.assertEqual(result[0]["view_count"], 0)
        self.assertEqual(result[0]["favorite_count"], 3)

    async def test_get_profile_accepts_bearer_tokens(self):
        session = FakeSession(
            {
                "data": {
                    "id": "42",
                    "screen_name": "alice",
                    "public_metrics": {"followers_count": 0, "following_count": 4},
                    "isBlueVerified": False,
                }
            }
        )
        client = XquikClient(api_key="plain-token", session=session)

        result = await client.get_profile("@alice")

        _, url, kwargs = session.requests[0]
        self.assertTrue(url.endswith("/api/v1/x/users/alice"))
        self.assertEqual(kwargs["headers"]["authorization"], "Bearer plain-token")
        self.assertEqual(result["username"], "alice")
        self.assertEqual(result["followers_count"], 0)
        self.assertFalse(result["is_blue_verified"])

    async def test_get_tweets_reads_nested_data(self):
        session = FakeSession(
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
        client = XquikClient(api_key="xq_test", session=session)

        result = await client.get_tweets("bob", 2)

        _, url, _ = session.requests[0]
        self.assertIn("/api/v1/x/users/bob/tweets?limit=2", url)
        self.assertEqual(result[0]["id"], "10")
        self.assertEqual(result[0]["author_username"], "bob")
        self.assertEqual(result[0]["reply_count"], 1)

    async def test_post_tweet_requires_action_configuration(self):
        client = XquikClient(api_key="xq_test")

        with self.assertRaises(XquikError):
            await client.post_tweet("hello")

    async def test_post_tweet_sends_account_and_reply(self):
        session = FakeSession({"tweet": {"id": "99"}})
        client = XquikClient(
            api_key="xq_test",
            account="@alice",
            actions_enabled=True,
            session=session,
        )

        result = await client.post_tweet("hello", "88")

        method, url, kwargs = session.requests[0]
        self.assertEqual(url, "https://xquik.com/api/v1/x/tweets")
        self.assertEqual(method, "POST")
        self.assertEqual(
            kwargs["json"],
            {
                "account": "@alice",
                "text": "hello",
                "replyToTweetId": "88",
            },
        )
        self.assertEqual(result["tweet_id"], "99")

    async def test_post_tweet_requires_tweet_id(self):
        session = FakeSession({"tweet": {}})
        client = XquikClient(
            api_key="xq_test",
            account="@alice",
            actions_enabled=True,
            session=session,
        )

        with self.assertRaisesRegex(XquikError, "missing tweet id"):
            await client.post_tweet("hello")

    async def test_http_errors_raise_backend_error(self):
        session = FakeSession(
            {"error": "insufficient_credits"}, status=402, reason="Payment Required"
        )
        client = XquikClient(api_key="xq_test", session=session)

        with self.assertRaisesRegex(XquikError, "insufficient_credits"):
            await client.search_tweets("ai", "Top", 1)

    def test_base_url_rejects_unsupported_schemes(self):
        with self.assertRaisesRegex(ValueError, "http or https"):
            XquikClient(api_key="xq_test", base_url="file:///tmp/xquik")


if __name__ == "__main__":
    unittest.main()
