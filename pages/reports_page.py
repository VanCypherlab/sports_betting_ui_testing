from pages.base_page import BackofficePage


class ReportsPage(BackofficePage):
    """Page Object for the reports page (backoffice-ui: src/resources/reports)."""

    URL_PATH = "/reports"
    HEADING_TEXT = "Reports"

    def __init__(self, page):
        super().__init__(page)
        self.refresh_button = page.get_by_role("button", name="Refresh")
