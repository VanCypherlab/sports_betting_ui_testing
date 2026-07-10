from playwright.sync_api import expect

from pages.players_page import PlayersPage
from tests.conftest import requires_admin_creds

pytestmark = requires_admin_creds


class TestPlayersPage:
    def test_page_loads(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        expect(players.table).to_be_visible()

    def test_username_search_does_not_crash(self, authenticated_page):
        players = PlayersPage(authenticated_page)
        players.goto()
        players.search_by_username("test")
        players.page.wait_for_timeout(500)
        expect(players.heading).to_be_visible()
