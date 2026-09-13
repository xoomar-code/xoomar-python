import io
import json
import unittest
from unittest import mock

from xoomar import Xoomar, XoomarRateLimited


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ClientTests(unittest.TestCase):
    def test_get_returns_data_and_keeps_meta(self):
        payload = {"data": [{"symbol": "GME"}], "updatedAt": "2026-09-13T00:00:00Z", "source": "xoomar.com", "attribution": "Free with attribution"}
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(json.dumps(payload).encode())) as u:
            x = Xoomar(api_key="k")
            rows = x.short_interest("GME")
            self.assertEqual(rows, [{"symbol": "GME"}])
            self.assertEqual(x.last_meta["source"], "xoomar.com")
            req = u.call_args[0][0]
            self.assertEqual(req.full_url, "https://xoomar.com/api/markets/short-interest?symbol=GME")
            self.assertEqual(req.get_header("X-api-key"), "k")

    def test_path_methods(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(b'{"data": []}')) as u:
            Xoomar().insiders("nvda")
            self.assertEqual(u.call_args[0][0].full_url, "https://xoomar.com/api/markets/insiders/nvda")
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(b'{"data": []}')) as u:
            Xoomar().large_holders("HIMS", form="13D", new=True)
            self.assertEqual(u.call_args[0][0].full_url, "https://xoomar.com/api/markets/large-holders?symbol=HIMS&form=13D&new=1")

    def test_rate_limit(self):
        import urllib.error
        err = urllib.error.HTTPError("https://xoomar.com/api/markets/cot", 429, "Too Many Requests", {"Retry-After": "12"}, io.BytesIO(b"slow down"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(XoomarRateLimited) as ctx:
                Xoomar().cot()
            self.assertEqual(ctx.exception.retry_after, 12)


if __name__ == "__main__":
    unittest.main()
