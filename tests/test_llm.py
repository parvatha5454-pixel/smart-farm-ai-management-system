import json
import unittest
from unittest import mock

import requests

from services.ai.llm import LLMError, OpenAICompatibleClient, get_client


def http(status=200, body=None):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = body if body is not None else {}
    return r


def client():
    return OpenAICompatibleClient("sk-secret-test-key", "https://example.test/v1/", "m", timeout=5)


class LLMClientTests(unittest.TestCase):
    def test_not_configured_without_key(self):
        self.assertFalse(OpenAICompatibleClient("", "https://x/v1", "m").is_configured())
        self.assertFalse(get_client({"AI_API_KEY": ""}).is_configured())
        with self.assertRaises(LLMError):
            OpenAICompatibleClient("", "https://x/v1", "m").chat([])

    def test_plain_reply(self):
        body = {"choices": [{"message": {"content": "Hello"}}]}
        with mock.patch("services.ai.llm.requests.post", return_value=http(200, body)) as p:
            r = client().chat([{"role": "user", "content": "hi"}])
        self.assertEqual(r, {"content": "Hello", "tool_calls": []})
        self.assertEqual(p.call_args[0][0], "https://example.test/v1/chat/completions")
        self.assertEqual(p.call_args[1]["timeout"], 5)

    def test_tool_call_parsed(self):
        body = {"choices": [{"message": {"content": None, "tool_calls": [
            {"id": "c1", "function": {"name": "get_pending_tasks", "arguments": "{}"}}]}}]}
        with mock.patch("services.ai.llm.requests.post", return_value=http(200, body)):
            r = client().chat([], tools=[{"x": 1}])
        self.assertEqual(r["tool_calls"], [{"id": "c1", "name": "get_pending_tasks", "arguments": {}}])

    def test_bad_tool_arguments_become_none(self):
        body = {"choices": [{"message": {"tool_calls": [
            {"id": "c1", "function": {"name": "x", "arguments": "{not json"}}]}}]}
        with mock.patch("services.ai.llm.requests.post", return_value=http(200, body)):
            r = client().chat([])
        self.assertIsNone(r["tool_calls"][0]["arguments"])

    def test_http_errors_have_safe_messages(self):
        cases = {401: "API key", 429: "rate limit", 500: "internal error", 400: "HTTP 400"}
        for status, text in cases.items():
            with mock.patch("services.ai.llm.requests.post", return_value=http(status, {"error": "sk-secret-test-key"})):
                with self.assertRaises(LLMError) as cm:
                    client().chat([])
            self.assertIn(text, str(cm.exception))
            self.assertNotIn("sk-secret-test-key", str(cm.exception))

    def test_timeout_and_connection_errors(self):
        for exc, text in ((requests.Timeout(), "too long"), (requests.ConnectionError(), "Could not reach")):
            with mock.patch("services.ai.llm.requests.post", side_effect=exc):
                with self.assertRaises(LLMError) as cm:
                    client().chat([])
            self.assertIn(text, str(cm.exception))

    def test_malformed_response(self):
        with mock.patch("services.ai.llm.requests.post", return_value=http(200, {"nope": 1})):
            with self.assertRaises(LLMError):
                client().chat([])


if __name__ == "__main__":
    unittest.main()
