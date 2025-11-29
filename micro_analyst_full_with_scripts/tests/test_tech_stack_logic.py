from mcp_tech_stack.server import run_tech_stack
from mcp_tech_stack.schemas import TechStackInput


def test_empty_html_returns_no_stack():
    payload = TechStackInput(raw_html=None)
    result = run_tech_stack(payload)
    assert result.success
    assert result.frameworks == []
    assert result.analytics == []
    assert result.cms is None
    assert result.cdn is None
    assert result.other == []
    assert result.error == "No HTML content provided."


def test_detects_frameworks_analytics_cms_cdn_other():
    html = """
    <html>
      <head>
        <script src="https://cdn.shopify.com/s/assets.js"></script>
        <script>window.dataLayer = window.dataLayer || [];</script>
        <script src="https://cdn.cloudflare.net/lib.js"></script>
      </head>
      <body>
        <div id="root">This site uses React and Next.js in the frontend.</div>
        <!-- wordpress and wp-content should also be detected -->
        <footer>Powered by WordPress, see /wp-content/themes/theme</footer>
        <span>Stripe and PayPal supported for payments</span>
      </body>
    </html>
    """
    payload = TechStackInput(raw_html=html)
    result = run_tech_stack(payload)

    assert result.success

    assert "React" in result.frameworks
    assert "Next.js" in result.frameworks

    assert "Google Tag Manager / dataLayer" in result.analytics

    assert result.cms == "WordPress"
    assert result.cdn == "Cloudflare"

    assert "Stripe" in result.other
    assert "PayPal" in result.other
