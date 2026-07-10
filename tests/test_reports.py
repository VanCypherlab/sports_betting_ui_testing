from playwright.sync_api import expect

from pages.reports_page import ReportsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestReportsPage:
    def test_page_loads(self, authenticated_page):
        ReportsPage(authenticated_page).goto()

    def test_refresh_does_not_crash(self, authenticated_page):
        reports = ReportsPage(authenticated_page)
        reports.goto()
        reports.refresh_button.click()
        expect(reports.heading).to_be_visible()
