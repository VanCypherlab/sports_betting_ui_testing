from pages.base_page import BackofficePage


class GlobalSettingsPage(BackofficePage):
    """Page Object for the platform-wide config page (backoffice-ui: src/resources/global-settings)."""

    URL_PATH = "/global-settings"
    HEADING_TEXT = "Global Settings"

    def __init__(self, page):
        super().__init__(page)

    def open_tab(self, tab_name: str):
        self.page.get_by_role("tab", name=tab_name).click()
