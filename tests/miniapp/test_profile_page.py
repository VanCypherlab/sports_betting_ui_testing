import pytest

from pages.miniapp.profile_page import ProfilePage

# No explicit miniapp-base-url skip needed -- authenticated_miniapp_page
# used below already depends on it.
pytestmark = pytest.mark.miniapp


class TestProfilePage:
    def test_page_loads(self, authenticated_miniapp_page):
        ProfilePage(authenticated_miniapp_page).goto()
