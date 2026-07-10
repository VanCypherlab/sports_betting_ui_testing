from playwright.sync_api import expect

from pages.audit_log_page import AuditLogPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestAuditLogPage:
    def test_page_loads(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        expect(audit.table).to_be_visible()

    def test_search_does_not_crash(self, authenticated_page):
        audit = AuditLogPage(authenticated_page)
        audit.goto()
        audit.search("login")
        audit.page.wait_for_timeout(500)
        expect(audit.heading).to_be_visible()
