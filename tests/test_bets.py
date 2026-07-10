from playwright.sync_api import expect

from pages.bets_page import BetsPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestBetsPage:
    def test_page_loads(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        expect(bets.table).to_be_visible()

    def test_status_filter_does_not_crash(self, authenticated_page):
        bets = BetsPage(authenticated_page)
        bets.goto()
        bets.filter_by_status("Unsettled")
        expect(bets.table).to_be_visible()
