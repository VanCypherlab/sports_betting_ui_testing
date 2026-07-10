from pages.profile_page import ProfilePage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestProfilePage:
    def test_page_loads(self, authenticated_page):
        ProfilePage(authenticated_page).goto()
