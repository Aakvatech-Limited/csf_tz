import ast
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from csf_tz import install


class TestSharedModuleInstall(TestCase):
    def test_no_duplicate_module_or_doctype_exports(self):
        root = Path(__file__).parent
        shared = {"AuthOTP", "Feedback", "AI Integration", "Trade In"}
        self.assertFalse(
            shared.intersection((root / "modules.txt").read_text().splitlines())
        )
        for source in root.rglob("*.json"):
            if "doctype" not in source.parts and "web_form" not in source.parts:
                continue
            document = json.loads(source.read_text())
            if isinstance(document, dict):
                self.assertNotIn(document.get("module"), shared, str(source))
                if document.get("doctype") == "DocType":
                    self.assertNotIn(
                        document.get("name"),
                        {"OTP Register", "AuthOTP Settings"},
                        str(source),
                    )

    def test_av_tools_is_required_and_otp_hooks_are_not_duplicated(self):
        source = (Path(__file__).parent / "hooks.py").read_text()
        assignments = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.parse(source).body
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"required_apps", "doctype_js", "doc_events"}
        }
        self.assertIn("av_tools", assignments["required_apps"])
        self.assertNotIn("authotp/api", str(assignments["doctype_js"]))
        self.assertNotIn("csf_tz.authotp", str(assignments["doc_events"]))

    @patch.object(install, "frappe")
    def test_missing_dependency_stops_before_changes(self, mock):
        mock.get_installed_apps.return_value = ["frappe", "csf_tz"]
        mock.throw.side_effect = RuntimeError("install av_tools first")
        with self.assertRaises(RuntimeError):
            install.before_migrate()
        mock.db.set_value.assert_not_called()

    @patch.object(install, "frappe")
    def test_legacy_ownership_is_transferred_without_deleting_data(self, mock):
        mock.get_installed_apps.return_value = ["frappe", "av_tools", "csf_tz"]
        mock.db.get_value.side_effect = lambda doctype, name, field: (
            "CSF TZ" if doctype == "DocType" else "csf_tz"
        )
        install.before_migrate()
        self.assertEqual(mock.db.set_value.call_count, 5)
        mock.db.delete.assert_not_called()
        mock.db.commit.assert_not_called()

    @patch.object(install, "frappe")
    def test_canonical_migration_is_idempotent(self, mock):
        mock.get_installed_apps.return_value = ["frappe", "av_tools", "csf_tz"]
        mock.db.get_value.return_value = "av_tools"
        install.before_migrate()
        install.before_migrate()
        mock.db.set_value.assert_not_called()

    def test_legacy_otp_endpoints_delegate_to_av_tools(self):
        from csf_tz.authotp.doctype.otp_register import otp_register

        canonical = MagicMock()
        with patch.object(otp_register, "canonical", canonical):
            otp_register.register_otp("payload")
            canonical.register_otp.assert_called_once_with("payload")
            otp_register.validate_otp("payload", "123456", submit=True)
            canonical.validate_otp.assert_called_once_with(
                "payload", "123456", submit=True
            )
            otp_register.validate_doc_otp("OTP-001", "123456")
            canonical.validate_doc_otp.assert_called_once_with("OTP-001", "123456")
