from pages.base_page import BackofficePage


class ProfilePage(BackofficePage):
    """Page Object for the self-service profile page (backoffice-ui: src/resources/profile)."""

    URL_PATH = "/profile"
    HEADING_TEXT = "Profile"
