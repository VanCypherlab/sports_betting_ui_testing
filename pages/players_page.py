from pages.base_page import BackofficePage


class PlayersPage(BackofficePage):
    """Page Object for the players list (backoffice-ui: src/resources/players)."""

    URL_PATH = "/players"
    HEADING_TEXT = "Players"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.player_id_search = page.get_by_placeholder("Player ID")
        self.username_search = page.get_by_placeholder("Username")
        self.match_id_search = page.get_by_placeholder("Match ID")

    def search_by_username(self, username: str):
        self.username_search.fill(username)
