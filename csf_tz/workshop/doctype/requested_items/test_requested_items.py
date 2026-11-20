import inspect

from frappe.tests.utils import FrappeTestCase

from csf_tz.workshop.doctype.requested_items.requested_items import RequestedItems


class TestRequestedItems(FrappeTestCase):
    def test_underscore_is_imported(self):
        """load_from_db calls _() on line 108; without 'from frappe import _' that is a NameError."""
        import csf_tz.workshop.doctype.requested_items.requested_items as mod

        self.assertTrue(callable(getattr(mod, "_", None)))

    def test_set_approval_status_does_not_commit(self):
        source = inspect.getsource(RequestedItems.set_approval_status)
        self.assertNotIn("frappe.db.commit", source)

    def test_set_issue_status_does_not_commit(self):
        source = inspect.getsource(RequestedItems.set_issue_status)
        self.assertNotIn("frappe.db.commit", source)

    def test_set_approval_status_does_not_db_set(self):
        """onload must not persist; db_set writes to the database on every form open."""
        source = inspect.getsource(RequestedItems.set_approval_status)
        self.assertNotIn("db_set", source)

    def test_set_issue_status_does_not_db_set(self):
        """onload must not persist; db_set writes to the database on every form open."""
        source = inspect.getsource(RequestedItems.set_issue_status)
        self.assertNotIn("db_set", source)
