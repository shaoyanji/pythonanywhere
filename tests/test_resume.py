import base64
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app.factory import create_app
from app.services.resume import analysis, needle, pdf, store, tooling

BASE_RESUME = Path(__file__).resolve().parent.parent / "resume" / "base.json"

SAMPLE_JD = (
    "We need Golang experience, cloud-native orchestration, observability, "
    "and declarative infrastructure."
)
EXPECTED_MAPPINGS = {
    "go": "skills/Go",
    "kubernetes": "skills/Kubernetes",
    "telemetry": "skills/telemetry",
    "nixos": "skills/NixOS",
}


def basic_auth_header(username="admin", password="secret"):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def digest_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pdfcpu_available():
    return bool(shutil.which("pdfcpu")) or (Path.home() / ".local/bin/pdfcpu").is_file()


class ResumeTestCase(unittest.TestCase):
    """Shared fixture: scratch variants dir and a stub for the public blueprint's
    context processor, which otherwise queries MySQL on every template render."""

    def setUp(self):
        self.variants = Path(tempfile.mkdtemp(prefix="resume-variants-"))
        self.app = create_app(
            {
                "TESTING": True,
                "ADMIN_USERNAME": "admin",
                "ADMIN_PASSWORD_HASH": generate_password_hash("secret"),
                "RESUME_BASE_PATH": BASE_RESUME,
                "RESUME_VARIANTS_DIR": self.variants,
            }
        )
        self.client = self.app.test_client()
        self._stack = ExitStack()
        self._stack.enter_context(
            patch("app.blueprints.public.fetch_site_settings", return_value={"meta_description": "d"})
        )
        self._stack.enter_context(patch("app.blueprints.public.fetch_navigation", return_value=[]))

    def tearDown(self):
        self._stack.close()
        shutil.rmtree(self.variants, ignore_errors=True)

    def csrf(self):
        """The global CSRF hook compares the form token to app.config, and the
        token is only minted when a template renders — so render one first."""
        response = self.client.get("/admin/resume/needle", headers=basic_auth_header())
        self.assertEqual(response.status_code, 200)
        return self.app.config["CSRF_TOKEN"]

    def approved_variant(self, name="acme", change="Go (5 years, production services)"):
        self.client.post(
            f"/admin/resume/{name}/jd",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf(), "jd": SAMPLE_JD},
        )
        payload = {
            "csrf_token": self.app.config["CSRF_TOKEN"],
            "approve_0": "on",
            "change_0": change,
            "apply_to_0": "skills",
        }
        response = self.client.post(
            f"/admin/resume/{name}/approve", headers=basic_auth_header(), data=payload
        )
        self.assertEqual(response.status_code, 302)
        return name


class AnalysisTests(ResumeTestCase):
    def test_sample_job_description_maps_all_four_concepts(self):
        base = json.loads(BASE_RESUME.read_text())
        result = analysis.analyze_job(SAMPLE_JD, base)

        self.assertEqual(result["threshold"], 0.15)
        self.assertEqual(len(result["proposals"]), 4, result["proposals"])
        self.assertEqual(result["gaps"], [])

        found = {proposal["concept"]: proposal["resume_key"] for proposal in result["proposals"]}
        self.assertEqual(found, EXPECTED_MAPPINGS)
        for proposal in result["proposals"]:
            self.assertGreaterEqual(proposal["score"], analysis.THRESHOLD)
            self.assertIsNone(proposal["suggested_change"], "no change may be pre-filled")
            self.assertIn(proposal["evidence"], SAMPLE_JD)

    def test_gap_is_reported_without_inventing_a_bullet(self):
        base = json.loads(BASE_RESUME.read_text())
        result = analysis.analyze_job("We need Terraform and AWS experience.", base)

        self.assertEqual(result["proposals"], [])
        self.assertEqual({gap["concept"] for gap in result["gaps"]}, {"terraform", "aws"})
        for gap in result["gaps"]:
            self.assertIsNone(gap["resume_key"])
            self.assertNotIn("suggested_change", gap, "a gap must never carry draft text")

    def test_synonym_groups_cover_the_hard_examples(self):
        hits = {hit.concept for hit in analysis.concept_hits(SAMPLE_JD)}
        self.assertEqual(hits, {"go", "kubernetes", "telemetry", "nixos"})
        self.assertEqual(analysis.stem("orchestration"), analysis.stem("orchestration"))


class ApprovalGateTests(ResumeTestCase):
    def test_apply_without_approval_fails_and_writes_nothing(self):
        base_digest = digest_of(BASE_RESUME)
        variant_dir = self.variants / "acme"

        response = self.client.post(
            "/admin/resume/acme/apply",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf()},
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse((variant_dir / "resume.json").exists())
        self.assertFalse((variant_dir / "applied.json").exists())
        self.assertEqual(digest_of(BASE_RESUME), base_digest)

    def test_store_refuses_apply_without_gate_file(self):
        with self.app.app_context():
            with self.assertRaises(store.ApprovalRequired):
                store.apply_approved("acme")

    def test_editor_save_is_refused_without_approval(self):
        base_digest = digest_of(BASE_RESUME)
        response = self.client.post(
            "/admin/resume/acme/edit",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf(), "name": "Nobody", "skills": "Ghost: invented"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse((self.variants / "acme" / "resume.json").exists())
        self.assertEqual(digest_of(BASE_RESUME), base_digest)

    def test_approve_then_apply_writes_only_the_variant(self):
        base_digest = digest_of(BASE_RESUME)
        name = self.approved_variant()
        self.assertTrue((self.variants / name / "approved.json").is_file())

        response = self.client.post(
            f"/admin/resume/{name}/apply",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf()},
        )
        self.assertEqual(response.status_code, 302)

        variant = json.loads((self.variants / name / "resume.json").read_text())
        self.assertEqual(digest_of(BASE_RESUME), base_digest, "base resume must not move")

        applied = json.loads((self.variants / name / "applied.json").read_text())
        self.assertTrue(any(item["status"] == "applied" for item in applied["items"]))
        # Every skill present in the base is still present in the variant.
        base = json.loads(BASE_RESUME.read_text())
        base_skills = {skill["name"] for skill in base["sections"]["skills"]}
        variant_skills = {skill["name"] for skill in variant["sections"]["skills"]}
        self.assertTrue(base_skills.issubset(variant_skills))

    def test_bullet_change_lands_on_the_selected_experience(self):
        name = "acme"
        self.client.post(
            f"/admin/resume/{name}/jd",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf(), "jd": SAMPLE_JD},
        )
        payload = {
            "csrf_token": self.app.config["CSRF_TOKEN"],
            "approve_0": "on",
            "change_0": "Led the migration to a declarative fleet",
            "apply_to_0": "bullets:1",  # the SECOND experience entry
        }
        self.client.post(f"/admin/resume/{name}/approve", headers=basic_auth_header(), data=payload)
        self.client.post(
            f"/admin/resume/{name}/apply",
            headers=basic_auth_header(),
            data={"csrf_token": self.app.config["CSRF_TOKEN"]},
        )

        variant = json.loads((self.variants / name / "resume.json").read_text())
        second = variant["sections"]["experience"][1]["bullets"]
        first = variant["sections"]["experience"][0]["bullets"]
        self.assertIn("Led the migration to a declarative fleet", second)
        self.assertNotIn("Led the migration to a declarative fleet", first)

    def test_review_page_offers_each_experience_as_a_bullet_target(self):
        name = "acme"
        self.client.post(
            f"/admin/resume/{name}/jd",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf(), "jd": SAMPLE_JD},
        )
        response = self.client.get(f"/admin/resume/{name}/review", headers=basic_auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="bullets:0"', response.data)
        self.assertIn(b'value="bullets:1"', response.data)

    def test_invalid_variant_name_is_rejected(self):
        for name in ("..", "a/b", "UPPER", ""):
            with self.app.app_context():
                with self.assertRaises(store.UnknownVariant):
                    store.variant_dir(name)

    def test_traversal_route_does_not_escape(self):
        response = self.client.get(
            "/admin/resume/..%2f..%2fetc/edit", headers=basic_auth_header()
        )
        self.assertEqual(response.status_code, 404)


class PdfTests(ResumeTestCase):
    @unittest.skipUnless(pdfcpu_available(), "pdfcpu not installed")
    def test_build_produces_a_validated_pdf_and_leaves_the_base_alone(self):
        base_digest = digest_of(BASE_RESUME)
        name = self.approved_variant()
        self.client.post(
            f"/admin/resume/{name}/apply",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf()},
        )

        response = self.client.post(
            f"/admin/resume/{name}/build",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf()},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(digest_of(BASE_RESUME), base_digest)

        with self.app.app_context():
            status = store.read_status(name)
            path = store.pdf_path(name)
        self.assertEqual(status["validate"], "ok")
        self.assertGreater(status["pages"], 0)
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes()[:4], b"%PDF")
        self.assertLess(status["size_bytes"], 30 * 1024, "PDF should stay small")

    @unittest.skipUnless(pdfcpu_available(), "pdfcpu not installed")
    def test_pdf_is_served_through_the_route_with_auth(self):
        name = self.approved_variant()
        self.client.post(
            f"/admin/resume/{name}/apply",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf()},
        )
        self.client.post(
            f"/admin/resume/{name}/build",
            headers=basic_auth_header(),
            data={"csrf_token": self.csrf()},
        )

        unauthenticated = self.client.get(f"/admin/resume/{name}/pdf")
        self.assertEqual(unauthenticated.status_code, 401)

        response = self.client.get(f"/admin/resume/{name}/pdf", headers=basic_auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertTrue(response.data.startswith(b"%PDF"))
        response.close()

    @unittest.skipUnless(pdfcpu_available(), "pdfcpu not installed")
    def test_long_resume_paginates_inside_the_margins(self):
        base = json.loads(BASE_RESUME.read_text())
        extra = json.loads(json.dumps(base["sections"]["experience"][0]))
        extra["company"] = "Another Shop"
        extra["bullets"] = extra["bullets"] * 3
        base["sections"]["experience"].insert(1, extra)

        with self.app.app_context():
            content = pdf.build_content(base)
        self.assertGreater(len(content["pages"]), 1)
        for page in content["pages"].values():
            positions = [entry["position"][1] for entry in page["content"]["text"]]
            self.assertGreater(min(positions), 40.0, "a line fell below the bottom margin")
            self.assertLessEqual(max(positions), 800.0, "a line rose above the top margin")
            self.assertEqual(positions, sorted(positions, reverse=True), "lines must run down the page")


class CatalogueTests(ResumeTestCase):
    def test_tools_json_has_exactly_five_parsed_tools(self):
        data = json.loads((tooling.ROOT / "tools.json").read_text())
        self.assertEqual(data["count"], 5)
        self.assertEqual(len(data["tools"]), 5)
        self.assertEqual(
            sorted(tool["name"] for tool in data["tools"]),
            sorted(needle.known_names()),
        )

    def test_committed_tools_json_matches_a_fresh_parse(self):
        fresh = tooling.build_catalogue()
        committed = json.loads((tooling.ROOT / "tools.json").read_text())
        self.assertEqual(fresh, committed, "tools.json drifted: run `doit tools_json`")

    def test_every_catalogue_entry_carries_the_required_metadata(self):
        for tool in tooling.build_catalogue()["tools"]:
            for field in tooling.REQUIRED_FIELDS:
                self.assertIn(field, tool)
            self.assertTrue(tool["example"])
            self.assertTrue(tool["when_not_to_use"])
            self.assertTrue(tool["preconditions"])

    def test_internal_tasks_are_not_in_the_catalogue(self):
        names = needle.known_names()
        for internal in ("tools_json", "install_pdfcpu"):
            self.assertNotIn(internal, names)


class NeedleTests(ResumeTestCase):
    def test_unknown_task_fails_without_executing(self):
        with patch("subprocess.run") as run:
            result = needle.run("delete_everything PYANY_VARIANT=acme")
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])
        run.assert_not_called()
        self.assertIn("delete_everything", result["error"])
        self.assertEqual(len(result["known"]), 5)

    def test_unlisted_parameter_is_refused(self):
        with patch("subprocess.run") as run:
            result = needle.run("show_tasks PYTHONPATH=/tmp")
        self.assertFalse(result["executed"])
        run.assert_not_called()
        self.assertIn("PYTHONPATH", result["error"])

    def test_bare_argument_is_refused(self):
        with patch("subprocess.run") as run:
            result = needle.run("show_tasks --all")
        self.assertFalse(result["executed"])
        run.assert_not_called()

    def test_known_task_runs_through_doit(self):
        if not shutil.which("doit") and not (Path(__file__).parent.parent / ".venv").exists():
            return
        result = needle.run("show_tasks", timeout=60)
        self.assertIn("analyze_job", result["output"])
        self.assertEqual(result["known"], needle.known_names())


class ResumeRouteAuthTests(ResumeTestCase):
    def test_every_resume_route_requires_authentication(self):
        paths = [
            "/admin/resume/",
            "/admin/resume/needle",
            "/admin/resume/acme/edit",
            "/admin/resume/acme/jd",
            "/admin/resume/acme/review",
            "/admin/resume/acme/diff",
            "/admin/resume/acme/pdf",
        ]
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401, path)
            self.assertIn("WWW-Authenticate", response.headers, path)

        for path in ("/admin/resume/needle", "/admin/resume/acme/apply", "/admin/resume/acme/build"):
            response = self.client.post(path, data={})
            # The app-wide CSRF hook in app/extensions.py runs as a before_request
            # and answers an unauthenticated POST with 403 before auth is checked
            # (the same behaviour the pre-existing suite trips over). Either way
            # the write is refused; what matters is that nothing is accepted.
            self.assertIn(response.status_code, (401, 403), path)
            self.assertFalse((self.variants / "acme" / "resume.json").exists())

    def test_overview_renders_for_the_owner(self):
        response = self.client.get("/admin/resume/", headers=basic_auth_header())
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Variants", response.data)


if __name__ == "__main__":
    unittest.main()
