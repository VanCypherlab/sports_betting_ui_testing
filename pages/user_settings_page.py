from pages.base_page import BackofficePage


class UserSettingsPage(BackofficePage):
    """Page Object for the self-service account settings page (backoffice-ui: src/resources/user-settings)."""

    URL_PATH = "/settings"
    HEADING_TEXT = "User Settings"
