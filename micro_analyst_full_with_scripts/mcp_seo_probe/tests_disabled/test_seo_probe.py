import unittest

from core.data_models import WebMetadata
from mcp_seo_probe.schemas import SEOProbeInput


class TestSEOProbeSchemas(unittest.TestCase):
    def test_input_model(self):
        meta = WebMetadata(title="Example Title", description="Description", h1=["H1"], h2=[])
        inp = SEOProbeInput(meta=meta, clean_text="Some example text")
        self.assertEqual(inp.meta.title, "Example Title")
        self.assertIn("example", inp.clean_text.lower())


if __name__ == "__main__":
    unittest.main()
