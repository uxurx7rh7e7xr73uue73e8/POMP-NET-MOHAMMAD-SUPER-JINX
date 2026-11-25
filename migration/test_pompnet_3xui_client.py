import unittest
from unittest.mock import Mock
from pompnet_3xui_client import ThreeXUIClient, ThreeXUIError


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.body.encode()


class ClientTests(unittest.TestCase):
    def make_client(self, body='{"success":true,"obj":[]}'):
        opener = Mock()
        opener.open.return_value = FakeResponse(body)
        return ThreeXUIClient("https://xui.example", api_token="test-token",
                              opener=opener), opener

    def test_list_clients_uses_v311_route_and_bearer(self):
        client, opener = self.make_client()
        self.assertEqual(client.list_clients(), [])
        req = opener.open.call_args.args[0]
        self.assertTrue(req.full_url.endswith("/panel/api/clients/list"))
        self.assertEqual(req.get_header("Authorization"), "Bearer test-token")

    def test_email_is_url_encoded(self):
        client, opener = self.make_client('{"success":true,"obj":{"email":"a b"}}')
        client.get_client("a b")
        req = opener.open.call_args.args[0]
        self.assertTrue(req.full_url.endswith("/get/a%20b"))

    def test_api_failure_is_not_silently_accepted(self):
        client, _ = self.make_client('{"success":false,"msg":"denied"}')
        with self.assertRaises(ThreeXUIError):
            client.list_clients()


if __name__ == "__main__":
    unittest.main()
