from pages.user_settings_page import UserSettingsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestUserSettingsPage:
    def test_page_loads(self, authenticated_page):
        UserSettingsPage(authenticated_page).goto()
