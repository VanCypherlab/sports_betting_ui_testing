from pages.base_page import BackofficePage


class SystemHealthPage(BackofficePage):
    """Page Object for the system health monitoring page (backoffice-ui: src/resources/system)."""

    URL_PATH = "/system-health"
    HEADING_TEXT = "System Health"

    def __init__(self, page):
        super().__init__(page)
        self.refresh_button = page.get_by_role("button", name="Refresh")
