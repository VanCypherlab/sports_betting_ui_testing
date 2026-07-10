from pages.base_page import BackofficePage


class AdminsPage(BackofficePage):
    """Page Object for the admin accounts list (backoffice-ui: src/resources/admins)."""

    URL_PATH = "/admins"
    HEADING_TEXT = "Admins"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.search_input = page.get_by_placeholder("Search admins...")

    def search(self, text: str):
        self.search_input.fill(text)
