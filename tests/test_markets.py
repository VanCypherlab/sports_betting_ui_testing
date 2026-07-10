from pages.markets_page import MarketsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestMarketsPage:
    def test_page_loads(self, authenticated_page):
        MarketsPage(authenticated_page).goto()

    def test_match_id_search_does_not_crash(self, authenticated_page):
        markets = MarketsPage(authenticated_page)
        markets.goto()
        markets.search_by_match_id("nonexistent-match-id")
        markets.page.wait_for_timeout(500)
        assert markets.heading.is_visible()
