import pytest
from playwright.sync_api import expect

from pages.miniapp.bet_page import BetPage

# No explicit miniapp-base-url skip needed -- authenticated_miniapp_page
# used below already depends on it.
pytestmark = pytest.mark.miniapp


class TestBetPage:
    def test_page_loads(self, authenticated_miniapp_page):
        BetPage(authenticated_miniapp_page).goto()

    def test_settled_tab_does_not_crash(self, authenticated_miniapp_page):
        bet = BetPage(authenticated_miniapp_page)
        bet.goto()
        bet.select_tab("Settled")
        expect(bet.heading).to_be_visible()
