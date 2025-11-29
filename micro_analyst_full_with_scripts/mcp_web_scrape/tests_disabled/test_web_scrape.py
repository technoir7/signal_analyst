import unittest

from mcp_web_scrape.schemas import WebScrapeInput, WebScrapeOutput


class TestWebScrapeSchemas(unittest.TestCase):
    def test_input_model(self):
        data = {"url": "https://example.com"}
        inp = WebScrapeInput(**data)
        self.assertEqual(str(inp.url), data["url"])

    def test_output_model_defaults(self):
        out = WebScrapeOutput(success=False, url="https://example.com")
        self.assertFalse(out.success)
        self.assertEqual(out.url, "https://example.com")


if __name__ == "__main__":
    unittest.main()
