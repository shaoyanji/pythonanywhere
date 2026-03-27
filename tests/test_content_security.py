import unittest

from app.factory import create_app
from app.services.content import render_markdown


class ContentSecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True})

    def test_render_markdown_strips_script_and_unsafe_links(self):
        payload = """
<script>alert(1)</script>
[bad](javascript:alert(1))
<a href="javascript:alert(2)">bad html link</a>
<strong>safe</strong>
"""
        with self.app.app_context():
            html = render_markdown(payload)

        self.assertNotIn("<script>", html)
        self.assertNotIn("javascript:alert", html)
        self.assertIn("<strong>safe</strong>", html)


if __name__ == "__main__":
    unittest.main()
