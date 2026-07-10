from pages.base_page import BackofficePage


class RolesPage(BackofficePage):
    """Page Object for the roles list (backoffice-ui: src/resources/roles)."""

    URL_PATH = "/roles"
    HEADING_TEXT = "Roles"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
        self.search_input = page.get_by_placeholder("Search roles...")

    def search(self, text: str):
        self.search_input.fill(text)
