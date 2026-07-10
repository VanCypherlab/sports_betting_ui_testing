from playwright.sync_api import expect

from pages.system_health_page import SystemHealthPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestSystemHealthPage:
    def test_page_loads(self, authenticated_page):
        SystemHealthPage(authenticated_page).goto()

    def test_refresh_does_not_crash(self, authenticated_page):
        system_health = SystemHealthPage(authenticated_page)
        system_health.goto()
        system_health.refresh_button.click()
        expect(system_health.heading).to_be_visible()
