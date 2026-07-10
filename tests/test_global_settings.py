from playwright.sync_api import expect

from pages.global_settings_page import GlobalSettingsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestGlobalSettingsPage:
    def test_page_loads(self, authenticated_page):
        GlobalSettingsPage(authenticated_page).goto()

    def test_switching_tab_does_not_crash(self, authenticated_page):
        settings = GlobalSettingsPage(authenticated_page)
        settings.goto()
        settings.open_tab("Wager Limits")
        expect(settings.heading).to_be_visible()
