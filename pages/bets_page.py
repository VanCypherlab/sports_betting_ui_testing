from pages.base_page import BackofficePage


class BetsPage(BackofficePage):
    """Page Object for the wagers/bets list (backoffice-ui: src/resources/bet)."""

    URL_PATH = "/bets"
    HEADING_TEXT = "Wagers"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.team_name_search = page.get_by_placeholder("Team name")
        self.wager_id_search = page.get_by_placeholder("Wager ID")
        self.match_id_search = page.get_by_placeholder("Match ID")
        self.status_filter = page.get_by_role("combobox").filter(has_text="All Status")

    def filter_by_status(self, option_text: str):
        self.status_filter.click()
        self.page.get_by_role("option", name=option_text).click()
