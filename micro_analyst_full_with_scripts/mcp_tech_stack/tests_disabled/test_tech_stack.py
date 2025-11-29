import unittest

from mcp_tech_stack.schemas import TechStackInput, TechStackOutput


class TestTechStackSchemas(unittest.TestCase):
    def test_input_model(self):
        html = "<html><head><script src='https://cdn.jsdelivr.net/npm/react'></script></head></html>"
        inp = TechStackInput(raw_html=html)
        self.assertIn("react", inp.raw_html.lower())

    def test_output_model_defaults(self):
        out = TechStackOutput(success=False, frameworks=[], analytics=[], other=[])
        self.assertFalse(out.success)
        self.assertEqual(out.frameworks, [])


if __name__ == "__main__":
    unittest.main()
