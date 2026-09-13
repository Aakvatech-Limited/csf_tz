import json
import unittest
from pathlib import Path


class TestJobCardsFrontendDependencies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[4]

    def test_vuetify_is_on_v3(self):
        package = json.loads((self.repo_root / "package.json").read_text())
        self.assertEqual(package["dependencies"]["vuetify"], "^3.7.19")

        lockfile = (self.repo_root / "yarn.lock").read_text()
        self.assertIn("vuetify@^3.7.19", lockfile)
        self.assertNotIn("vuetify@^2", lockfile)
        self.assertNotIn('version "2.', lockfile)

    def test_jobcards_does_not_load_vuetify_2_assets(self):
        page_js = (
            self.repo_root / "csf_tz/csf_tz/page/jobcards/jobcards.js"
        ).read_text()
        self.assertNotIn("vuetify@2", page_js)
        self.assertNotIn("node_modules/vuetify/dist/vuetify.min.css", page_js)

    def test_bundle_uses_vuetify_3_styles(self):
        bundle_js = (
            self.repo_root / "csf_tz/public/js/jobcards/jobcards.bundle.js"
        ).read_text()
        self.assertIn('import "vuetify/styles"', bundle_js)
        self.assertIn("createVuetify", bundle_js)

    def test_event_bus_does_not_use_vue_2_constructor(self):
        bus_js = (self.repo_root / "csf_tz/public/js/jobcards/bus.js").read_text()
        self.assertNotIn("new Vue(", bus_js)
        self.assertIn("$emit", bus_js)
        self.assertIn("$on", bus_js)
        self.assertIn("$off", bus_js)


if __name__ == "__main__":
    unittest.main()
