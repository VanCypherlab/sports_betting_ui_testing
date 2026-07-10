from pages.base_page import BackofficePage


class MarketsPage(BackofficePage):
    """Page Object for the markets list (backoffice-ui: src/resources/markets/market)."""

    URL_PATH = "/markets"
    HEADING_TEXT = "Markets"

    def __init__(self, page):
        super().__init__(page)
        self.match_id_search = page.get_by_placeholder("Search by Match ID...")

    def search_by_match_id(self, match_id: str):
        self.match_id_search.fill(match_id)
