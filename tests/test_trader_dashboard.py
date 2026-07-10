from pages.trader_dashboard_page import TraderDashboardPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestTraderDashboardPage:
    def test_page_loads(self, authenticated_page):
        TraderDashboardPage(authenticated_page).goto()
