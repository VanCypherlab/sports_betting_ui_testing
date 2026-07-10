from pages.alerts_page import AlertsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestAlertsPage:
    def test_page_loads(self, authenticated_page):
        AlertsPage(authenticated_page).goto()
