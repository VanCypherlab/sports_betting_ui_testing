from playwright.sync_api import expect

from pages.reconciliation_page import ReconciliationPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestReconciliationPage:
    def test_page_loads(self, authenticated_page):
        reconciliation = ReconciliationPage(authenticated_page)
        reconciliation.goto()
        expect(reconciliation.table).to_be_visible()

    def test_refresh_does_not_crash(self, authenticated_page):
        reconciliation = ReconciliationPage(authenticated_page)
        reconciliation.goto()
        reconciliation.refresh_button.click()
        expect(reconciliation.table).to_be_visible()
