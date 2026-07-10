from pages.base_page import BackofficePage


class ResolutionPage(BackofficePage):
    """Page Object for the cross-provider entity resolution console (backoffice-ui: src/resources/resolution)."""

    URL_PATH = "/resolution"
    HEADING_TEXT = "Resolution Console"

    def __init__(self, page):
        super().__init__(page)
        self.table = page.get_by_role("table")
