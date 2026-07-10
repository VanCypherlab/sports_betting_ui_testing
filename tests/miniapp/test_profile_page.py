import pytest

from pages.miniapp.profile_page import ProfilePage
from tests.miniapp.conftest import requires_miniapp_base_url

pytestmark = [requires_miniapp_base_url, pytest.mark.miniapp]


class TestProfilePage:
    def test_page_loads(self, authenticated_miniapp_page):
        ProfilePage(authenticated_miniapp_page).goto()
