import base64
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app.factory import create_app


def basic_auth_header(username="admin", password="secret"):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


class RouteSmokeTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "ADMIN_USERNAME": "admin",
                # The gate authenticates against ADMIN_PASSWORD_HASH. This fixture
                # set ADMIN_PASSWORD, which nothing reads, so every "authenticated"
                # request here was really a 401 (or a crash inside
                # check_password_hash(None, ...) that looked like a DB error).
                "ADMIN_PASSWORD_HASH": generate_password_hash("secret"),
                "ADMIN_PASSWORD": "secret",
                "ENABLE_ADMIN_DEPLOY": False,
            }
        )
        self.client = self.app.test_client()

    def _stub_public_context(self, stack):
        """Every template render runs the public blueprint's context processor,
        which queries MySQL. Stubbed only in the admin tests that render: the
        bootstrap test below must keep failing honestly if the app cannot render
        without a database."""
        stack.enter_context(
            patch("app.blueprints.public.fetch_site_settings", return_value={"meta_description": "d"})
        )
        stack.enter_context(patch("app.blueprints.public.fetch_navigation", return_value=[]))

    def _public_patches(self):
        return ExitStack()

    def _json_headers(self):
        return {
            "Accept": "application/json",
            "X-Requested-With": "json-runtime",
        }

    def test_public_routes_render(self):
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_site_settings",
                    return_value={
                        "hero_title": "Hero",
                        "hero_intro": "Intro",
                        "meta_description": "desc",
                        "footer_note": "foot",
                    },
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_navigation",
                    return_value=[
                        {"label": "Home", "href": "/", "kind": "public"},
                        {"label": "Notes", "href": "/notes", "kind": "public"},
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_page",
                    side_effect=lambda slug: {
                        "slug": slug,
                        "title": slug.title(),
                        "body_html": "<p>Body</p>",
                    },
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_posts",
                    return_value=[
                        {
                            "slug": "first-note",
                            "title": "First Note",
                            "excerpt": "Excerpt",
                        }
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_experiments",
                    return_value=[
                        {
                            "slug": "aki-json-dom",
                            "title": "AKI JSON-DOM navigation",
                            "summary": "Summary",
                            "demo_path": None,
                        }
                    ],
                )
            )

            for path in ("/", "/notes", "/experiments", "/about"):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, path)

        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json, {"ok": True})

    def test_public_routes_bootstrap_without_content_tables(self):
        for path in ("/", "/notes", "/experiments", "/about"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_public_routes_support_json_patches(self):
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_site_settings",
                    return_value={
                        "hero_title": "Hero",
                        "hero_intro": "Intro",
                        "meta_description": "desc",
                        "footer_note": "foot",
                    },
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_navigation",
                    return_value=[
                        {"label": "Home", "href": "/", "kind": "public"},
                        {"label": "Notes", "href": "/notes", "kind": "public"},
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_page",
                    side_effect=lambda slug: {
                        "slug": slug,
                        "title": slug.title(),
                        "body_html": "<p>Body</p>",
                    },
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_posts",
                    return_value=[
                        {
                            "slug": "first-note",
                            "title": "First Note",
                            "excerpt": "Excerpt",
                            "body_html": "<p>Body</p>",
                        }
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_post",
                    return_value={
                        "slug": "first-note",
                        "title": "First Note",
                        "excerpt": "Excerpt",
                        "body_html": "<p>Body</p>",
                    },
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_experiments",
                    return_value=[
                        {
                            "slug": "aki-json-dom",
                            "title": "AKI JSON-DOM navigation",
                            "summary": "Summary",
                            "demo_path": "/experiments/wasm-kelly-criterion/demo",
                        }
                    ],
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_experiment",
                    return_value={
                        "slug": "aki-json-dom",
                        "title": "AKI JSON-DOM navigation",
                        "summary": "Summary",
                        "body_html": "<p>Body</p>",
                        "demo_path": "/experiments/wasm-kelly-criterion/demo",
                        "source_path": "app/experiments/aki.py",
                    },
                )
            )

            for path in (
                "/",
                "/notes",
                "/notes/first-note",
                "/experiments",
                "/experiments/aki-json-dom",
                "/about",
            ):
                response = self.client.get(path, headers=self._json_headers())
                self.assertEqual(response.status_code, 200, path)
                self.assertIn("#content", response.json)
                self.assertIn("#site-nav", response.json)
                self.assertIn("title", response.json)

    def test_kelly_calculator_returns_targeted_patch(self):
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_site_settings",
                    return_value={"meta_description": "desc", "footer_note": "foot"},
                )
            )
            stack.enter_context(
                patch(
                    "app.blueprints.public.fetch_navigation",
                    return_value=[
                        {"label": "Home", "href": "/", "kind": "public"},
                        {"label": "Experiments", "href": "/experiments", "kind": "public"},
                    ],
                )
            )

            response = self.client.get(
                "/experiments/wasm-kelly-criterion/demo",
                headers=self._json_headers(),
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("#content", response.json)

            calculate = self.client.get(
                "/experiments/wasm-kelly-criterion/demo/calculate?probability=60&reward=50&risk=25"
            )
            self.assertEqual(calculate.status_code, 200)
            self.assertIn("#demo-result", calculate.json)
            self.assertIn("40.0", calculate.json["#demo-result"]["innerHTML"])

    def test_admin_routes_require_authentication(self):
        for path in ("/admin/", "/admin/content", "/admin/prompts", "/admin/deploy"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401, path)
            self.assertIn("WWW-Authenticate", response.headers)

        response = self.client.post("/admin/content", data={"type": "post"})
        self.assertEqual(response.status_code, 401)

    def test_admin_get_routes_have_no_side_effects(self):
        with ExitStack() as stack:
            self._stub_public_context(stack)
            stack.enter_context(patch("app.blueprints.admin.fetch_content_summary", return_value={"pages": 1}))
            response = self.client.get("/admin/", headers=basic_auth_header())
            self.assertEqual(response.status_code, 200)

        with ExitStack() as stack:
            self._stub_public_context(stack)
            stack.enter_context(patch("app.blueprints.admin.fetch_admin_content", return_value=[]))
            response = self.client.get(
                "/admin/content?type=post",
                headers=basic_auth_header(),
            )
            self.assertEqual(response.status_code, 200)

        with ExitStack() as stack:
            self._stub_public_context(stack)
            stack.enter_context(patch("app.blueprints.admin.fetch_prompt_runs", return_value=[]))
            response = self.client.get("/admin/prompts", headers=basic_auth_header())
            self.assertEqual(response.status_code, 200)

        with ExitStack() as stack:
            self._stub_public_context(stack)
            stack.enter_context(patch("app.blueprints.admin.run_deploy_tasks"))
            response = self.client.get("/admin/deploy", headers=basic_auth_header())
            self.assertEqual(response.status_code, 200)

    def test_admin_mutations_are_post_only(self):
        routes = {rule.rule: rule for rule in self.app.url_map.iter_rules() if rule.rule.startswith("/admin")}
        self.assertEqual(routes["/admin/content"].methods - {"HEAD", "OPTIONS"}, {"GET", "POST"})
        self.assertEqual(routes["/admin/deploy"].methods - {"HEAD", "OPTIONS"}, {"GET", "POST"})

    def test_deploy_post_is_env_gated(self):
        # This test used to post with no CSRF token, so it asserted a world where
        # the CSRF hook did not exist and could only ever fail with 403. Auth is
        # now checked before CSRF, and an authenticated write still needs a token,
        # so the token is supplied here and the assertion is about the env gate.
        self.app.config["CSRF_TOKEN"] = "test-token"
        with ExitStack() as stack:
            self._stub_public_context(stack)
            stack.enter_context(patch("app.services.deploy.run_command"))
            response = self.client.post(
                "/admin/deploy",
                headers=basic_auth_header(),
                data={"csrf_token": "test-token"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Deploy actions are disabled", response.data)

    def test_prompt_output_is_escaped_in_admin_view(self):
        with ExitStack() as stack:
            self._stub_public_context(stack)
            stack.enter_context(
                patch(
                    "app.blueprints.admin.fetch_prompt_runs",
                    return_value=[
                        {
                            "title": "legacy",
                            "kind": "legacy-message",
                            "input_text": "<b>prompt</b>",
                            "output_text": "<script>alert(1)</script>",
                        }
                    ],
                )
            )
            response = self.client.get("/admin/prompts", headers=basic_auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", response.data)


if __name__ == "__main__":
    unittest.main()
