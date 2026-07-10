from pages.boost_page import BoostPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestBoostPage:
    def test_page_loads(self, authenticated_page):
        BoostPage(authenticated_page).goto()
