from pages.base_page import BackofficePage


class MatchesPage(BackofficePage):
    """Page Object for the matches list (backoffice-ui: src/resources/matches)."""

    URL_PATH = "/matches"
    HEADING_TEXT = "Matches"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.lifecycle_filter = page.get_by_role("combobox", name="Lifecycle filter")
        self.sport_filter = page.get_by_role("combobox", name="Sport filter")
        self.league_filter = page.get_by_role("combobox", name="League filter")
        self.pic_filter = page.get_by_role("combobox", name="PIC filter")

    def filter_by_lifecycle(self, option_text: str):
        self.lifecycle_filter.click()
        self.page.get_by_role("option", name=option_text, exact=True).click()
