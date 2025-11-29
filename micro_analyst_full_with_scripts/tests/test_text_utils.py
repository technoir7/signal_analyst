from utils.text_utils import clean_html_to_text, truncate_text


def test_clean_html_to_text_strips_scripts_and_styles():
    html = """
    <html>
      <head>
        <style>.hidden { display:none; }</style>
        <script>console.log("test");</script>
      </head>
      <body>
        <h1>Title</h1>
        <p>Some <strong>content</strong> here.</p>
      </body>
    </html>
    """
    text = clean_html_to_text(html)
    assert "Title" in text
    assert "Some content here." in text
    assert "console.log" not in text
    assert "display:none" not in text


def test_truncate_text_behaviour():
    text = "abcdefghij"
    assert truncate_text(text, 20) == text
    assert truncate_text(text, 5) == "abcde"
    # type: ignore[arg-type]
    assert truncate_text(None, 5) is None  # noqa: E501
