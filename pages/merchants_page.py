from pages.base_page import BackofficePage


class MerchantsPage(BackofficePage):
    """Page Object for the merchants list (backoffice-ui: src/resources/merchants)."""

    URL_PATH = "/merchants"
    HEADING_TEXT = "Merchants"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
